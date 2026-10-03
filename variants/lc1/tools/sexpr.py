"""Small KiCad s-expression reader/writer; preserves quoted atoms."""
import json
import re


class Quoted(str):
    pass


def parse(text):
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text)
    stack = []
    root = None
    for token in tokens:
        if token == '(':
            value = []
            if stack:
                stack[-1].append(value)
            else:
                root = value
            stack.append(value)
        elif token == ')':
            stack.pop()
        else:
            stack[-1].append(Quoted(json.loads(token)) if token.startswith('"') else token)
    assert not stack
    return root


def dumps(value):
    if isinstance(value, list):
        return '(' + ' '.join(dumps(x) for x in value) + ')'
    if isinstance(value, Quoted):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def items(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def get(node, key, default=None):
    return next(iter(items(node, key)), default)


def prop(node, key):
    return next(x for x in items(node, 'property') if x[1] == key)


def replace(node, key, value):
    old = get(node, key)
    if old is not None:
        node[node.index(old)] = value
    else:
        node.append(value)
