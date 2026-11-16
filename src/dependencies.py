"""Deterministic exported-resource resolution; never infer DLC mount order.

Optional dependency-policy.json records filename priorities (larger wins), explicit
name overrides, TXD parents and scoped texture filenames. This is user-supplied
mount evidence, not a claim to reconstruct GTA's active DLC configuration.
"""
import collections
import json
import re
import xml.etree.ElementTree as ET


def load_policy(source):
    path = source / 'dependency-policy.json'
    return json.loads(path.read_text()) if path.exists() else {}


def joaat(name):
    """RAGE's case-insensitive Jenkins one-at-a-time name hash."""
    value = 0
    for byte in name.lower().encode('ascii'):
        value = (value + byte) & 0xffffffff
        value = (value + (value << 10)) & 0xffffffff
        value ^= value >> 6
    value = (value + (value << 3)) & 0xffffffff
    value ^= value >> 11
    return (value + (value << 15)) & 0xffffffff


def archetype_name_index(source):
    """Index only explicit YTYP names; hash collisions remain ambiguous."""
    names = collections.defaultdict(set)
    for path in sorted(source.glob('*.ytyp.xml')):
        for item in ET.parse(path).getroot().findall('.//archetypes/Item'):
            name = item.findtext('name', '').strip().lower()
            if name:
                try:
                    names[joaat(name)].add(name)
                except UnicodeEncodeError:
                    continue
    return names


def resolve_hash_reference(value, names):
    """Resolve hash-only XML references only when one YTYP name matches."""
    match = re.fullmatch(r'hash_([0-9a-fA-F]{8})', value.strip())
    if not match:
        return value.lower(), None
    number = int(match.group(1), 16)
    candidates = sorted(names.get(number, ()))
    if len(candidates) == 1:
        return candidates[0], {'reference': value, 'status': 'resolved', 'name': candidates[0]}
    status = 'ambiguous' if candidates else 'unresolved'
    return value.lower(), {'reference': value, 'status': status, 'candidates': candidates}


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


class TextureCatalog:
    """Opt-in scoped material bindings; legacy flat exports remain the default."""
    def __init__(self, source):
        import hashlib
        self.source = source
        self.policy = load_policy(source)
        self.enabled = self.policy.get('scoped_textures', False)
        self.records = {}
        self.diagnostics = {}
        self.asset_txds = dict(self.policy.get('asset_txds', {}))
        definitions = collections.defaultdict(list)
        for path in sorted(source.glob('*.ytyp.xml')):
            for item in ET.parse(path).getroot().findall('.//archetypes/Item'):
                name, txd = item.findtext('name'), item.findtext('textureDictionary')
                if name and txd:
                    key = name.lower()
                    definitions[key].append((self.policy.get('priorities', {}).get(path.name, 0), txd.lower()))
        for name, definitions_for_name in definitions.items():
            if name in self.asset_txds: continue
            priority = max(rank for rank, txd in definitions_for_name)
            choices = {txd for rank, txd in definitions_for_name if rank == priority}
            if len(choices) == 1: self.asset_txds[name] = next(iter(choices))
            else: self.diagnostics[name] = {'dictionary_conflict': sorted(choices)}
        self.legacy = {p.stem.lower(): {'path':p,'used':False} for p in sorted(source.glob('*.dds'))}
        self._hash = hashlib.sha256

    def for_asset(self, asset):
        if not self.enabled: return self.legacy
        txd = self.asset_txds.get(asset.lower())
        if not txd:
            self.diagnostics.setdefault(asset, {}).update(missing_dictionary=True)
            return {}
        names = set()
        current = txd; seen = set()
        while current and current not in seen:
            seen.add(current)
            names.update(self.policy.get('textures', {}).get(current, {}))
            current = self.policy.get('txd_parents', {}).get(current, '')
        bindings = {}
        if current: self.diagnostics[asset] = {'parent_cycle': sorted(seen)}
        for name in sorted(names):
            path, evidence = texture_lookup(self.source, txd, name, self.policy)
            if path is None:
                self.diagnostics.setdefault(asset, {})[name] = evidence
                continue
            relative = path.relative_to(self.source.resolve()).as_posix()
            target = 'scoped_' + self._hash(relative.encode()).hexdigest() + '.dds'
            record = self.records.setdefault(relative, {'path':path,'target':target,'used':False})
            bindings[name] = record
        return bindings

    def used_records(self):
        return [t for t in (self.records.values() if self.enabled else self.legacy.values()) if t['used']]
