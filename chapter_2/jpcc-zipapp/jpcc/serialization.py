# This file implements a simple symbolic expression serialization format.

def to_exprs_str(obj, pretty=True, indent=4):
    """Serialize the object as symbolic expressions (lists).
    The first item in each list is the type of the object.
    The object's items or key/value property pairs then follow.
    Example:
        @dataclass
        class Bar:
            enabled: bool
        @dataclass
        class Foo:
            name: str
            count: int
            things: list
            props: dict
            bar: Bar
        f = Foo("Dennis Ritchie", 42, [1,"a"], {"b":2}, Bar(True))
        to_exprs(f) -> (Foo name "Dennis Ritchie" count 42 things (list 1 "a")
            props (dict "b" 2) bar (Bar enabled True))
    """

    def to_exprs(obj):
        "Recursively convert the object into lists."
        if isinstance(obj, (type(None), bool, int, float)):
            return obj
        elif isinstance(obj, str):
            return f'"{obj}"'
        elif isinstance(obj, (tuple, list, set)):
            exprs = [obj.__class__.__name__] + [to_exprs(x) for x in obj]
            return exprs
        elif hasattr(obj, 'items') or hasattr(obj, '__dict__'):
            exprs = [obj.__class__.__name__]
            pairs = (obj.__dict__ if hasattr(obj, '__dict__') else obj).items()
            for k, v in pairs:
                if v is None and hasattr(obj, '__dict__'):
                    # suppress empty object properties
                    continue
                exprs.append(k)
                exprs.append(to_exprs(v))
            return exprs
        else:
            raise Exception(f"Don't know how to serialize {obj}")
    
    def exprs_to_str(exprs):
        "Format the expressions as a string (compact)."
        if isinstance(exprs, list):
            strs = []
            for subexpr in exprs:
                if isinstance(subexpr, list):
                    strs.append(exprs_to_str(subexpr))
                else:
                    strs.append(f"{subexpr}")
            text = "(%s)" % " ".join(strs)
        else:
            text = f"{exprs}"
        return text

    def exprs_to_str_pretty(exprs, indent, _level=0):
        "Format the expressions as a string (pretty-printed)."
        if not isinstance(exprs, list):
            text = f"{exprs}"
        else:
            text = "(" + exprs[0]
            if exprs[0] in ['tuple', 'list', 'set']:
                for subexpr in exprs[1:]:
                    lead2 = (" " * indent) * (_level+1)
                    text += "\n" + lead2 + exprs_to_str_pretty(subexpr, indent, _level+1)
                lead = (" " * indent) * _level
                text += "\n" + lead + ")"
            else:
                it = iter(exprs[1:])
                pairs = list(zip(it, it))
                if len(pairs) == 0:
                    text += ")"
                else:
                    for k, v in pairs:
                        lead2 = (" " * indent) * (_level+1)
                        text += "\n" + lead2 + f"{k} "
                        if isinstance(v, list):
                            text += exprs_to_str_pretty(v, indent, _level+1)
                        else:
                            text += f"{v}"
                    lead = (" " * indent) * _level
                    text += "\n" + lead + ")"
        return text

    exprs = to_exprs(obj)
    if pretty:
        return exprs_to_str_pretty(exprs, indent)
    else:
        return exprs_to_str(exprs)
