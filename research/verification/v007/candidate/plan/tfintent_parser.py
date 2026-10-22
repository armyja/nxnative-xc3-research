#!/usr/bin/env python3
"""Dedicated matcher: [kd] header -> validated [gs-res] HIT -> [tf-intent] line with the same frame/pass/VS/PS/GS.

The gs-res part is the audited frozen parser (gsres_parser_base.py, unchanged copy). This module adds the intent line
parser and a chain state machine. A gs-res HIT is NOT terminal: the observation is only complete when the matching
[tf-intent] line arrives. active=unknown/inactive/active are all valid completions: the line records observed replay
intent, never the actual TF/GPU state. association stays none.
"""
import re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gsres_parser_base as base

TARGET_PS = '2e16c536b845ea0e'
TARGET_GS = '95bfab6122539993'

TAG = '[tf-intent] '
PREFIX = '[dm] [nvn-mtl] '   # the production MLOG wrapper; only this exact prefix is accepted
U64 = r'(0|[1-9][0-9]*)'
HEX = r'(0|0x[0-9a-f]+)'
VSPS = re.compile(r'^[0-9a-f]{16}(?:_b|_bf)?$')
GSKEY = re.compile(r'^[0-9a-f]{16}$')
KD_HDR = re.compile(r'^\[kd\] F\d+ pass \d+ ')
ACTIVE = {'unknown', 'inactive', 'active'}
PAUSE = {'unknown', 'running', 'paused'}
REASONS = {'none', 'no-event', 'end-without-begin', 'end-while-inactive', 'begin-while-paused', 'begin-while-active',
           'pause-without-active', 'resume-without-pause', 'index-unsupported', 'plural-opaque', 'draw-opaque',
           'invalid-opaque', 'bad-payload', 'bad-record', 'bad-kind', 'seq-saturated'}
RE_INTENT = re.compile(
    r'^' + re.escape(TAG) +
    r'frame=' + U64 + r' pass=' + U64 + r' vs=(\S+) ps=(\S+) gs=(\S+) final_pass_association=none '
    r'interpretation=observed-replay-intent active=(\w+) pause=(\w+) reason=([\w-]+) '
    r'seq=' + U64 + r' events=' + U64 + r' copies=' + U64 + r' depth=(-?[0-9]+) '
    r'(?:bound0=valid addr=' + HEX + r' size=' + U64 + r'|bound0=none) '
    r'begin=' + HEX + r' end=' + HEX + r' draw=' + HEX + r'$')

class ParseError(ValueError):
    pass

def parse_tf_intent(line):
    """Parse one bare or [dm] [nvn-mtl]-prefixed [tf-intent] line. Any other wrapper is rejected (no substring search)."""
    s = line.rstrip('\n\r')
    raw = s
    if s.startswith(PREFIX + TAG):
        s = s[len(PREFIX):]
    elif not s.startswith(TAG):
        raise ParseError('not a tf-intent line')
    if not s.startswith(TAG):
        raise ParseError('not a tf-intent line')
    if s.startswith(TAG + 'diagnostic-error'):
        return {'raw': raw, 'diagnostic_error': True}
    m = RE_INTENT.match(s)
    if not m:
        raise ParseError('tf-intent field syntax')
    g = m.groups()
    r = {
        'raw': raw, 'diagnostic_error': False,
        'frame': int(g[0]), 'pass_counter': int(g[1]), 'vs': g[2], 'ps': g[3], 'gs': g[4],
        'active': g[5], 'pause': g[6], 'reason': g[7],
        'seq': int(g[8]), 'events': int(g[9]), 'copies': int(g[10]), 'depth': int(g[11]),
        'bound0_valid': g[12] is not None, 'bound0_addr': int(g[12], 16) if g[12] else None,
        'bound0_size': int(g[13]) if g[13] is not None else None,
        'begin': int(g[14], 16), 'end': int(g[15], 16), 'draw': int(g[16], 16),
    }
    if r['active'] not in ACTIVE: raise ParseError('active value %r' % r['active'])
    if r['pause'] not in PAUSE: raise ParseError('pause value %r' % r['pause'])
    if r['reason'] not in REASONS: raise ParseError('reason value %r' % r['reason'])
    U64MAX = (1 << 64) - 1
    for k in ('frame', 'pass_counter', 'seq', 'events', 'copies', 'begin', 'end', 'draw'):
        if not (0 <= r[k] <= U64MAX): raise ParseError('%s u64 range' % k)
    if not (-2147483648 <= r['depth'] <= 2147483647): raise ParseError('depth i32 range')
    if r['events'] < r['copies']: raise ParseError('copies > events')
    if not VSPS.match(r['vs']): raise ParseError('vs token (16 lowerhex + bare/_b/_bf)')
    if not VSPS.match(r['ps']): raise ParseError('ps token (16 lowerhex + bare/_b/_bf)')
    if not GSKEY.match(r['gs']): raise ParseError('gs token (16 lowerhex)')
    if r['bound0_valid']:
        if not (0 <= r['bound0_addr'] <= U64MAX) or not (0 <= r['bound0_size'] <= U64MAX): raise ParseError('bound0 u64 range')
        if r['bound0_addr'] + r['bound0_size'] > U64MAX: raise ParseError('bound0 addr+size overflow')
    return r

class TfIntentChain:
    """[kd] -> [gs-res] -> [tf-intent] chain. Terminal only on a complete chain or an explicit mismatch/error."""
    def __init__(self, target_gs=TARGET_GS, target_ps=TARGET_PS):
        self.base = base.GsResStateMachine(target_gs, target_ps)
        self.terminal = None; self.result = None; self.why = None
        self.hdr = None; self.record = None; self.intent = None; self.raw = []

    def _term(self, result, why):
        if self.terminal is None:
            self.terminal, self.result, self.why = why, result, why
        return self.terminal

    def feed(self, line):
        if self.terminal is not None:
            return self.terminal
        s = line.rstrip('\n\r')
        if s.startswith('[kd]'):
            if KD_HDR.match(s):
                return self._feed_header(s)
            if s.startswith('[kd] F'):
                return self._term('invalid', 'malformed [kd] header')
            self.raw.append(s)          # production [kd] attr/stream/uniform sub-line: ignored, never a header
            return None
        if '[tf-intent]' in s and not (s.startswith(TAG) or s.startswith(PREFIX + TAG)):
            return self._term('invalid', 'non-exact tf-intent prefix')   # no substring/wrapped forms are accepted
        if s.startswith(TAG) or s.startswith(PREFIX + TAG):
            self.raw.append(s)
            if self.record is None or self.base.result != 'hit':
                return self._term('invalid', 'tf-intent before a validated gs-res hit')
            try:
                it = parse_tf_intent(s)
            except ParseError as e:
                return self._term('invalid', 'tf-intent parse/validate: %s' % e)
            if it.get('diagnostic_error'):
                return self._term('diagnostic-error', 'tf-intent diagnostic-error')
            h = self.hdr or {}
            if (it['frame'], it['pass_counter']) != (h.get('frame'), h.get('pass_counter')):
                return self._term('invalid', 'tf-intent frame/pass differs from header')
            if it['vs'] != h.get('vs') or it['ps'] != h.get('ps'):
                return self._term('invalid', 'tf-intent VS/PS differs from header')
            if it['gs'] != self.base.target_gs:
                return self._term('invalid', 'tf-intent GS differs from target')
            self.intent = it
            return self._term('hit', 'hit (tf-intent chain)')
        t = self.base.feed(s)
        self.hdr = self.base.hdr; self.record = self.base.record
        if t is not None and self.base.result != 'hit':
            return self._term(self.base.result, self.base.terminal)
        return None

    def _feed_header(self, s):
        t = self.base.feed(s)
        self.hdr = self.base.hdr; self.record = self.base.record
        if t is not None and self.base.result != 'hit':
            return self._term(self.base.result, self.base.terminal)
        return None

    def snapshot(self):
        return {'terminal': self.terminal, 'result': self.result, 'why': self.why,
                'header': self.hdr, 'record': self.record, 'intent': self.intent, 'raw': list(self.raw)}
