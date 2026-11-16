"""Deterministic exported-resource resolution; never infer DLC mount order.

Optional dependency-policy.json records filename priorities (larger wins), explicit
name overrides, TXD parents and scoped texture filenames. This is user-supplied
mount evidence, not a claim to reconstruct GTA's active DLC configuration.
"""
import collections
import json
import xml.etree.ElementTree as ET


def load_policy(source):
    path = source / 'dependency-policy.json'
    return json.loads(path.read_text()) if path.exists() else {}


def choose(name, paths, policy, overrides):
    label = lambda p: p[0].name + '#' + p[1] if isinstance(p, tuple) else p.name
    override = overrides.get(name)
    if override is not None:
        matches = [p for p in paths if label(p) == override]
        if len(matches) != 1: raise ValueError('Invalid dependency override: ' + name)
        return matches[0]
    priority = policy.get('priorities', {})
    rank = lambda p: priority.get(p[0].name if isinstance(p, tuple) else p.name, 0)
    best = max(map(rank, paths))
    winners = [p for p in paths if rank(p) == best]
    return winners[0] if len(winners) == 1 else None


def texture_lookup(source, dictionary, texture, policy=None):
    """Return scoped child/parent texture or explicit missing/cycle diagnosis."""
    policy = load_policy(source) if policy is None else policy
    seen = []; current = dictionary.lower()
    while current:
        if current in seen: return None, {'cycle': seen + [current]}
        seen.append(current)
        name = policy.get('textures', {}).get(current, {}).get(texture.lower())
        if name:
            path = (source / name).resolve()
            if source.resolve() not in path.parents: raise ValueError('Texture path escapes source')
            return (path if path.is_file() else None), {'chain': seen, 'file': name}
        current = policy.get('txd_parents', {}).get(current, '')
    return None, {'chain': seen, 'missing': texture}


def resolve(source, overrides=None):
    policy = load_policy(source)
    overrides = {**policy.get('overrides', {}), **(overrides or {})}
    candidates = collections.defaultdict(list)
    for pattern in ('*.ydr.xml', '*.yft.xml'):
        for path in sorted(source.glob(pattern)):
            candidates[path.name.split('.rpf_')[-1][:-8].lower()].append(path)
    for path in sorted(source.glob('*.ydd.xml')):
        for item in ET.parse(path).getroot().findall('Item'):
            name = item.findtext('Name', '').lower()
            if name: candidates[name].append((path, name))
    resolved = {}; ambiguous = {}; provenance = {}
    label = lambda p: p[0].name + '#' + p[1] if isinstance(p, tuple) else p.name
    for name, paths in sorted(candidates.items()):
        chosen = choose(name, paths, policy, overrides)
        provenance[name] = {'candidates': [label(p) for p in paths], 'selected': label(chosen) if chosen else None}
        if chosen is not None: resolved[name] = chosen
        else: ambiguous[name] = [label(p) for p in paths]
    aliases = collections.defaultdict(set)
    for path in sorted(source.glob('*.ytyp.xml')):
        for item in ET.parse(path).getroot().findall('.//archetypes/Item'):
            name, asset = item.findtext('name'), item.findtext('assetName')
            if name and asset: aliases[name.lower()].add(asset.lower())
    # Fixed-point resolution supports chains without order dependence; cycles stay missing.
    pending = dict(aliases)
    while pending:
        progressed = False
        for name, assets in list(pending.items()):
            if len(assets) == 1 and next(iter(assets)) in resolved:
                asset = next(iter(assets))
                if name not in candidates: resolved[name] = resolved[asset]
                del pending[name]; progressed = True
        if not progressed: break
    for name, assets in aliases.items():
        if len(assets) > 1 and name not in candidates:
            resolved.pop(name, None); ambiguous[name] = sorted(assets)
    return resolved, {'ambiguous_drawables': ambiguous, 'provenance': provenance,
                      'unresolved_archetype_assets': {n: sorted(a) for n,a in aliases.items() if n not in resolved},
                      'unsupported_dictionary_exports': [],
                      'precedence': 'Explicit filename priorities only; equal-rank conflicts unresolved.'}
