"""Local JSON adapter for the user-tested Windows JianYing 11.6.0.14552 profile.

Never operates the editor, decrypts drafts, installs drafts, or writes source media.
prepare_draft() returns deep copies; write_copy() only writes a new directory.
"""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import time
import uuid

PROFILE = 'windows-jianying-11.6.0.14552'
FULL_CROP = dict(upper_left_x=0, upper_left_y=0, upper_right_x=1,
                 upper_right_y=0, lower_left_x=0, lower_left_y=1,
                 lower_right_x=1, lower_right_y=1)


def path_key(value):
    if not value or not Path(value).is_absolute():
        raise ValueError('Media paths must be absolute')
    return os.path.normcase(str(Path(value).resolve()))


def full_crop(material):
    crop = material.get('crop')
    return not crop or (set(crop) == set(FULL_CROP) and all(
        isinstance(crop[k], (int, float)) and math.isclose(crop[k], v, abs_tol=1e-8)
        for k, v in FULL_CROP.items()))


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def catalog_index(sources):
    result = {}
    for item in sources:
        key = path_key(item['path'])
        if key in result:
            raise ValueError('Duplicate source catalog path: ' + item['path'])
        if item['kind'] not in ('video', 'photo'):
            raise ValueError('Visual source kind must be video or photo')
        for field in ('width', 'height'):
            if not number(item.get(field)) or item[field] <= 0:
                raise ValueError('Full-source width/height required')
        if item['kind'] == 'video' and (not number(item.get('duration_us')) or item['duration_us'] <= 0):
            raise ValueError('Full video duration_us required, not shot duration')
        result[key] = item
    return result


def registry_entries(meta):
    return [entry for group in meta.get('draft_materials', [])
            if group.get('type') == 0 for entry in group.get('value', [])]


def validate_draft(content, meta, sources=None, profile=PROFILE):
    """Read-only structural audit. Cache filesystem access per unique media path."""
    started = time.perf_counter()
    errors, warnings, paths = [], [], {}
    if profile != PROFILE:
        errors.append('Unsupported profile: validate a minimal example for this version first')
    catalog = catalog_index(sources) if sources is not None else None
    registry = {}
    for entry in registry_entries(meta):
        identity = entry.get('id')
        if not identity or identity in registry:
            errors.append('Missing/duplicate bin registration id')
        registry[identity] = entry
    all_materials = {}
    for array in content.get('materials', {}).values():
        if not isinstance(array, list):
            continue
        for material in array:
            if not isinstance(material, dict) or not material.get('id'):
                continue
            if material['id'] in all_materials:
                errors.append('Duplicate material id: ' + material['id'])
            all_materials[material['id']] = material
            if material.get('path'):
                try:
                    key = path_key(material['path'])
                    if key not in paths:
                        paths[key] = Path(material['path']).is_file()
                    if not paths[key]:
                        errors.append('Missing media: ' + material['path'])
                except (ValueError, OSError) as exc:
                    errors.append(str(exc))
    visuals = {m['id']: m for m in content.get('materials', {}).get('videos', [])}
    for identity, material in visuals.items():
        try:
            key = path_key(material.get('path'))
            entry = registry.get(material.get('local_material_id'))
            filename = Path(material['path']).name
            if material.get('material_name') != filename or ('name' in material and material['name'] != filename):
                errors.append('Visual display name must equal original filename: ' + identity)
            if entry and entry.get('extra_info') != filename:
                errors.append('Bin display name must equal original filename: ' + identity)
            if not entry or path_key(entry.get('file_Path')) != key:
                errors.append('Visual/bin path association invalid: ' + identity)
            if material.get('material_id') != '':
                errors.append('Local visual material_id must be empty for this profile: ' + identity)
            if not full_crop(material):
                errors.append('Non-full material crop requires a separately verified method: ' + identity)
            if catalog is not None:
                source = catalog.get(key)
                if source is None:
                    errors.append('Visual is not in approved full-source catalog: ' + identity)
                else:
                    fields = ['width', 'height'] + (['duration'] if source['kind'] == 'video' else [])
                    for field in fields:
                        expected = source['duration_us'] if field == 'duration' else source[field]
                        if material.get(field) != expected or (entry and entry.get(field) != expected):
                            errors.append('Full-source metadata mismatch ' + identity + ': ' + field)
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
    segment_ids = set()
    for track in content.get('tracks', []):
        for segment in track.get('segments', []):
            sid = segment.get('id', '')
            if not sid or sid in segment_ids:
                errors.append('Missing/duplicate segment id: ' + str(sid))
            segment_ids.add(sid)
            mid = segment.get('material_id')
            if mid not in all_materials:
                errors.append('Dangling timeline material: ' + str(mid))
                continue
            material = visuals.get(mid)
            if material is None:
                continue
            if 'name' in segment and segment['name'] != Path(material['path']).name:
                errors.append('Segment display name must equal original filename: ' + sid)
            clip = segment.get('clip') or {}
            scale = clip.get('scale', {'x': 1, 'y': 1})
            transform = clip.get('transform', {'x': 0, 'y': 0})
            if any(not number(scale.get(axis)) or scale[axis] <= 0 for axis in ('x', 'y')):
                errors.append('Invalid scale: ' + sid)
            elif not math.isclose(scale['x'], scale['y'], rel_tol=1e-8):
                errors.append('Non-uniform visual scale needs explicit separate treatment: ' + sid)
            if any(not number(transform.get(axis)) for axis in ('x', 'y')):
                errors.append('Invalid transform: ' + sid)
            if segment.get('common_keyframes'):
                warnings.append('Keyframes require adapter-specific review; not validated: ' + sid)
            if material.get('type') != 'photo':
                interval = segment.get('source_timerange') or {}
                # Native profile may omit a zero-valued start when serializing.
                start, duration = interval.get('start', 0), interval.get('duration')
                if (not number(start) or not number(duration) or start < 0 or duration <= 0
                        or not number(material.get('duration')) or start + duration > material['duration']):
                    errors.append('Invalid source range: ' + sid)
    return {'structural_status': 'failed' if errors else 'passed', 'errors': errors,
            'warnings': warnings, 'profile': profile, 'unique_media_paths_checked': len(paths),
            'visual_materials': len(visuals), 'segments': len(segment_ids),
            'full_source_catalog_check': 'performed' if catalog is not None else 'not_provided',
            'elapsed_seconds': round(time.perf_counter() - started, 6),
            'ui_reveal_bin': 'not_tested', 'ui_reveal_timeline': 'not_tested',
            'ui_reset': 'not_tested', 'ui_save_reopen': 'not_tested',
            'migration_relink': 'not_tested', 'media_decode': 'not_performed'}


def prepare_draft(content, meta, sources, transforms=None, profile=PROFILE):
    """Adapter hook for a newly generated/local-copy draft, NOT a crop repairer.

    sources: approved full-source metadata, [{path,kind,width,height,duration_us}].
    transforms: {segment_id: {scale: positive scalar, x: float, y: float}}.
    Source ranges/audio/text are retained; visual display names use original filenames.
    """
    if profile != PROFILE:
        raise ValueError('Unverified target version: ' + profile)
    started = time.perf_counter()
    d, m = copy.deepcopy(content), copy.deepcopy(meta)
    catalog = catalog_index(sources)
    groups = m.setdefault('draft_materials', [])
    group = next((g for g in groups if g.get('type') == 0), None)
    if group is None:
        group = {'type': 0, 'value': []}
        groups.append(group)
    entries = registry_entries(m)
    by_path = {}
    for entry in entries:
        key = path_key(entry.get('file_Path'))
        if key in by_path:
            raise ValueError('Duplicate existing bin path; preserve and inspect instead of merging')
        by_path[key] = entry
    now = int(time.time() * 1e6)
    for material in d.get('materials', {}).get('videos', []):
        key = path_key(material.get('path'))
        if key not in catalog:
            raise ValueError('Original visual path not in approved source catalog: ' + str(material.get('path')))
        source = catalog[key]
        if not full_crop(material):
            raise ValueError('Refusing to erase an existing material crop; regenerate composition explicitly')
        expected_type = 'photo' if source['kind'] == 'photo' else 'video'
        if material.get('type') != expected_type:
            raise ValueError('Visual kind mismatch')
        material.update(width=source['width'], height=source['height'], material_id='')
        filename = Path(material['path']).name
        material['material_name'] = filename
        if 'name' in material:
            material['name'] = filename
        if source['kind'] == 'video':
            material['duration'] = source['duration_us']
        entry = by_path.get(key)
        if entry is None:
            entry = dict(ai_group_type='', create_time=now // 1000000, duration=material.get('duration', 0),
                         enter_from=0, extra_info=Path(material['path']).name,
                         file_Path=str(Path(material['path'])).replace('\\', '/'), id=str(uuid.uuid4()).upper(),
                         import_time=now // 1000000, import_time_ms=now, item_source=1,
                         material_color_tag='', md5='', metetype=expected_type,
                         roughcut_time_range={'start': 0, 'duration': material.get('duration', 0)},
                         sub_time_range={'start': -1, 'duration': -1}, type=0,
                         width=source['width'], height=source['height'])
            group.setdefault('value', []).append(entry)
            by_path[key] = entry
        elif (entry.get('width') != source['width'] or entry.get('height') != source['height']
              or (source['kind'] == 'video' and entry.get('duration') != source['duration_us'])):
            raise ValueError('Existing bin metadata differs: inspect rather than overwrite')
        material['local_material_id'] = entry['id']
        entry['extra_info'] = filename
    segments = {s['id']: s for t in d.get('tracks', []) for s in t.get('segments', [])}
    visuals = {v['id']: v for v in d.get('materials', {}).get('videos', [])}
    visual_ids = set(visuals)
    for segment in segments.values():
        if segment.get('material_id') in visuals and 'name' in segment:
            segment['name'] = Path(visuals[segment['material_id']]['path']).name
    for sid, values in (transforms or {}).items():
        segment = segments.get(sid)
        if segment is None or segment.get('material_id') not in visual_ids:
            raise ValueError('Transform must target an existing visual segment: ' + sid)
        if segment.get('common_keyframes'):
            raise ValueError('Refusing to override existing keyframes: ' + sid)
        scale, x, y = values['scale'], values.get('x', 0), values.get('y', 0)
        if not all(number(v) for v in (scale, x, y)) or scale <= 0:
            raise ValueError('Finite positive uniform scale and finite position required')
        clip = segment.setdefault('clip', {})
        clip.update(scale={'x': scale, 'y': scale}, transform={'x': x, 'y': y})
    report = validate_draft(d, m, sources, profile)
    if report['errors']:
        raise ValueError('; '.join(report['errors']))
    report['prepare_and_validate_seconds'] = round(time.perf_counter() - started, 6)
    return d, m, report


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Need decoded JSON from a verified version-matched reader; input untouched') from exc


def write_copy(content, meta, report, output):
    """Write only a NEW standalone intermediate copy; never installs into JianYing."""
    target = Path(output).resolve()
    target.mkdir(parents=True, exist_ok=False)
    d, m = copy.deepcopy(content), copy.deepcopy(meta)
    uid = str(uuid.uuid4()).upper()
    d.update(id=uid, name=target.name)
    m.update(draft_id=uid, draft_name=target.name, draft_fold_path=str(target),
             draft_root_path=str(target.parent))
    for filename, value in [('draft_content.json', d), ('draft_meta_info.json', m)]:
        with (target / filename).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
    if load_json(target / 'draft_content.json') != d or load_json(target / 'draft_meta_info.json') != m:
        raise ValueError('JSON read-back mismatch')
    result = dict(report, json_roundtrip='passed', native_codec_roundtrip='not_performed',
                  output=str(target), delivery='intermediate_copy_not_installed')
    with (target / 'engineering_check.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['audit', 'prepare'])
    parser.add_argument('--content', required=True)
    parser.add_argument('--meta', required=True)
    parser.add_argument('--sources', help='approved full-source metadata JSON list')
    parser.add_argument('--transforms', help='segment transform JSON mapping')
    parser.add_argument('--profile', required=True)
    parser.add_argument('--output', help='new independent intermediate directory for prepare')
    args = parser.parse_args()
    content, meta = load_json(args.content), load_json(args.meta)
    sources = load_json(args.sources) if args.sources else None
    if args.mode == 'audit':
        result = validate_draft(content, meta, sources, args.profile)
    else:
        if sources is None or not args.output:
            parser.error('prepare requires --sources and --output')
        transforms = load_json(args.transforms) if args.transforms else None
        d, m, report = prepare_draft(content, meta, sources, transforms, args.profile)
        result = write_copy(d, m, report, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result['structural_status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
