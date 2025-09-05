# servers/my_local_srv.py
# ============================================================
#  CFG Tools MCP Server
#  - eliminate_epsilon: elimina ε-producciones y devuelve pasos
#  - cyk_parse: convierte a CNF, corre CYK y arma una derivación
# ------------------------------------------------------------
#  Requisitos:
#    pip install "mcp[cli]" python-dotenv
#  Ejecución (desde el host):
#    await host.connect_server("local", "python", ["servers/my_local_srv.py"])
# ============================================================

from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional, Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("CFG Tools")

# ----------------------------
# Utilidades de gramática
# ----------------------------
EPSILON_TOKENS = {"ε", "EPS", "EPSILON", "epsilon"}

@dataclass
class Grammar:
    start: str
    prods: Dict[str, List[Tuple[str, ...]]]

def _tokenize_rhs(rhs: str) -> Tuple[str, ...]:
    rhs = rhs.strip()
    if rhs in EPSILON_TOKENS or rhs == "":
        return tuple()
    return tuple(s for s in rhs.split() if s)

def parse_grammar(text: str, start_symbol: Optional[str]=None) -> "Grammar":
    prods: Dict[str, List[Tuple[str, ...]]] = {}
    first_lhs = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "->" not in line:
            raise ValueError(f"Línea inválida (sin '->'): {line}")
        lhs, rhs_all = line.split("->", 1)
        lhs = lhs.strip()
        if first_lhs is None:
            first_lhs = lhs
        alts = [a.strip() for a in rhs_all.split("|")]
        for alt in alts:
            prods.setdefault(lhs, []).append(_tokenize_rhs(alt))
    if not prods:
        raise ValueError("Gramática vacía")
    start = start_symbol or first_lhs
    if start not in prods:
        prods.setdefault(start, [])
    return Grammar(start=start, prods=prods)

def pretty_grammar(g: "Grammar") -> str:
    lines = []
    for A, rhss in g.prods.items():
        if not rhss:
            lines.append(f"{A} -> /* sin producciones */")
            continue
        alts = [("ε" if len(rhs)==0 else " ".join(rhs)) for rhs in rhss]
        lines.append(f"{A} -> " + " | ".join(alts))
    return "\n".join(lines)

def nonterminals(g: "Grammar") -> Set[str]:
    return set(g.prods.keys())

def terminals(g: "Grammar") -> Set[str]:
    nts = nonterminals(g)
    ts: Set[str] = set()
    for rhss in g.prods.values():
        for rhs in rhss:
            for s in rhs:
                if s not in nts:
                    ts.add(s)
    return ts

# --------------------------------------------
# Eliminación de epsilon-producciones (ε)
# --------------------------------------------
def eliminate_epsilon_internal(g: "Grammar"):
    steps: List[str] = []
    nullable: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for A, rhss in g.prods.items():
            if A in nullable:
                continue
            for rhs in rhss:
                if len(rhs) == 0 or all((X in nullable) for X in rhs):
                    nullable.add(A)
                    changed = True
                    steps.append(f"{A} es anulable")
                    break

    new_prods: Dict[str, Set[Tuple[str, ...]]] = {A: set() for A in g.prods}
    S = g.start
    original_allows_epsilon = any(len(rhs) == 0 for rhs in g.prods.get(S, []))

    for A, rhss in g.prods.items():
        for rhs in rhss:
            if len(rhs) == 0:
                continue
            idx_null = [i for i, X in enumerate(rhs) if X in nullable]
            n = len(idx_null)
            variants: Set[Tuple[str, ...]] = {rhs}
            for mask in range(1, 1 << n):
                rr = list(rhs)
                for j in range(n):
                    if (mask >> j) & 1:
                        rr[idx_null[j]] = None
                cand = tuple(s for s in rr if s is not None)
                variants.add(cand)
            for v in variants:
                if len(v) == 0:
                    if A == S and original_allows_epsilon:
                        new_prods[A].add(tuple())
                        steps.append(f"{A} -> ε (permitida porque S derivaba ε)")
                else:
                    new_prods[A].add(v)

    if original_allows_epsilon:
        new_prods[S].add(tuple())

    steps.append("Epsilon-producciones eliminadas.")
    return Grammar(start=g.start, prods={A: sorted(list(vs)) for A, vs in new_prods.items()}), steps

# ---------------------------------------------------
# Eliminación de unitarias A -> B
# ---------------------------------------------------
def remove_unit_productions(g: "Grammar"):
    steps: List[str] = []
    nts = list(nonterminals(g))
    unit: Dict[str, Set[str]] = {A: {A} for A in nts}
    changed = True
    while changed:
        changed = False
        for A in nts:
            for rhs in g.prods.get(A, []):
                if len(rhs) == 1 and rhs[0] in g.prods:
                    B = rhs[0]
                    before = len(unit[A])
                    unit[A] |= unit[B]
                    if len(unit[A]) > before:
                        changed = True
    new_prods: Dict[str, Set[Tuple[str, ...]]] = {A: set() for A in nts}
    for A in nts:
        for B in unit[A]:
            for rhs in g.prods.get(B, []):
                if len(rhs) == 1 and rhs[0] in g.prods:
                    continue
                new_prods[A].add(rhs)
    steps.append("Producciones unitarias eliminadas.")
    return Grammar(start=g.start, prods={A: sorted(list(vs)) for A, vs in new_prods.items()}), steps

# ---------------------------------------------------
# Remover símbolos inútiles
# ---------------------------------------------------
def remove_useless_symbols(g: "Grammar"):
    steps: List[str] = []
    nts = nonterminals(g)
    ts = terminals(g)

    generating: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for A, rhss in g.prods.items():
            if A in generating:
                continue
            for rhs in rhss:
                if all((sym in ts) or (sym in generating) for sym in rhs):
                    generating.add(A)
                    changed = True
                    break
    steps.append(f"Generadores: {sorted(generating)}")

    reachable: Set[str] = {g.start}
    changed = True
    while changed:
        changed = False
        for A in list(reachable):
            for rhs in g.prods.get(A, []):
                for sym in rhs:
                    if sym in nts and sym not in reachable:
                        reachable.add(sym)
                        changed = True
    steps.append(f"Alcanzables: {sorted(reachable)}")

    keep = generating & reachable
    new_prods: Dict[str, List[Tuple[str, ...]]] = {}
    for A in keep:
        kept_rhss = []
        for rhs in g.prods.get(A, []):
            if all((sym in ts) or (sym in keep) for sym in rhs):
                kept_rhss.append(rhs)
        if kept_rhss:
            new_prods[A] = kept_rhss

    steps.append("Símbolos inútiles removidos.")
    return Grammar(start=g.start, prods=new_prods), steps

# ---------------------------------------------------
# CNF
# ---------------------------------------------------
def to_cnf(g: "Grammar"):
    steps: List[str] = []
    nts = set(g.prods.keys())
    ts = terminals(g)

    term_map: Dict[str, str] = {}
    new_prods: Dict[str, List[Tuple[str, ...]]] = {A: [] for A in g.prods}

    def get_T_for(t: str) -> str:
        if t not in term_map:
            T = f"T_{t}"
            i = 1
            while T in nts or T in g.prods:
                T = f"T_{t}_{i}"
                i += 1
            term_map[t] = T
        return term_map[t]

    for A, rhss in g.prods.items():
        for rhs in rhss:
            if len(rhs) >= 2:
                new_rhs = [get_T_for(s) if s in ts else s for s in rhs]
                new_prods[A].append(tuple(new_rhs))
            else:
                new_prods[A].append(rhs)

    for t, T in term_map.items():
        new_prods[T] = [(t,)]
        steps.append(f"Nuevo símbolo {T} -> {t}")

    counter = 1
    def fresh_nt() -> str:
        nonlocal counter
        while True:
            X = f"X_{counter}"
            counter += 1
            if X not in new_prods and X not in g.prods and X not in term_map.values():
                return X

    bin_prods: Dict[str, List[Tuple[str, ...]]] = {}
    for A, rhss in new_prods.items():
        out = []
        for rhs in rhss:
            if len(rhs) <= 2:
                out.append(rhs)
            else:
                curr = list(rhs)
                left = curr[0]
                rest = curr[1:]
                prev_left = left
                while len(rest) > 1:
                    X = fresh_nt()
                    bin_prods.setdefault(X, [])
                    out.append((prev_left, X))
                    prev_left = X
                    rest = rest[1:]
                out.append((prev_left, rest[0]))
        bin_prods[A] = out

    steps.append("Gramática binarizada (CNF).")
    return Grammar(start=g.start, prods=bin_prods), steps

# ---------------------------------------------------
# CYK con backpointers
# ---------------------------------------------------
def cyk(g: "Grammar", tokens: List[str]):
    n = len(tokens)
    if n == 0:
        ok = any(len(rhs) == 0 for rhs in g.prods.get(g.start, []))
        return ok, [], "ε" if ok else None

    term_index: Dict[str, Set[str]] = {}
    pair_index: Dict[Tuple[str, str], Set[str]] = {}
    for A, rhss in g.prods.items():
        for rhs in rhss:
            if len(rhs) == 1:
                term_index.setdefault(rhs[0], set()).add(A)
            elif len(rhs) == 2:
                pair_index.setdefault((rhs[0], rhs[1]), set()).add(A)

    table: List[List[Set[str]]] = [[set() for _ in range(n)] for _ in range(n)]
    back: Dict[Tuple[int, int, str], Any] = {}

    for i, t in enumerate(tokens):
        for A in term_index.get(t, []):
            table[i][0].add(A)
            back[(i, 1, A)] = t

    for l in range(2, n + 1):
        for i in range(0, n - l + 1):
            for split in range(1, l):
                left_len = split
                right_len = l - split
                for B in table[i][left_len - 1]:
                    for C in table[i + split][right_len - 1]:
                        for A in pair_index.get((B, C), []):
                            if A not in table[i][l - 1]:
                                table[i][l - 1].add(A)
                                back[(i, l, A)] = (split, B, C)

    accepted = (g.start in table[0][n - 1])

    def build_tree(i: int, l: int, A: str) -> Any:
        val = back.get((i, l, A))
        if val is None:
            return A
        if isinstance(val, str):
            return (A, val)
        split, B, C = val
        left = build_tree(i, split, B)
        right = build_tree(i + split, l - split, C)
        return (A, left, right)

    def tree_to_brackets(node: Any) -> str:
        if isinstance(node, tuple):
            if len(node) == 2 and isinstance(node[1], str):
                return f"({node[0]} {node[1]})"
            if len(node) == 3:
                return f"({node[0]} {tree_to_brackets(node[1])} {tree_to_brackets(node[2])})"
        return str(node)

    derivation = None
    if accepted:
        tree = build_tree(0, n, g.start)
        derivation = tree_to_brackets(tree)

    pretty_table: List[List[List[str]]] = []
    for l in range(1, n + 1):
        row: List[List[str]] = []
        for i in range(0, n - l + 1):
            row.append(sorted(list(table[i][l - 1])))
        pretty_table.append(row)

    return accepted, pretty_table, derivation

# ============================================================
# TOOLS
# ============================================================

@mcp.tool()
def eliminate_epsilon(grammar_text: str, start_symbol: Optional[str] = None) -> Dict[str, Any]:
    g = parse_grammar(grammar_text, start_symbol=start_symbol)
    g1, s1 = eliminate_epsilon_internal(g)
    g2, s2 = remove_unit_productions(g1)
    g3, s3 = remove_useless_symbols(g2)
    out = pretty_grammar(g3)
    return {
        "grammar": out,
        "steps": s1 + s2 + s3,
        "stats": {
            "nonterminals": sorted(list(nonterminals(g3))),
            "terminals": sorted(list(terminals(g3))),
            "start": g3.start
        }
    }

@mcp.tool()
def cyk_parse(
    grammar_text: str,
    sentence: str,
    start_symbol: Optional[str] = None,
    epsilon_symbol: str = "ε"
) -> Dict[str, Any]:
    tokens = [t for t in sentence.strip().split() if t]
    g0 = parse_grammar(grammar_text, start_symbol=start_symbol)
    g1, s1 = eliminate_epsilon_internal(g0)
    g2, s2 = remove_unit_productions(g1)
    g3, s3 = remove_useless_symbols(g2)
    cnf, s4 = to_cnf(g3)
    acc, table, deriv = cyk(cnf, tokens)
    return {
        "accepted": acc,
        "table": table,
        "derivation": deriv if acc else None,
        "cnf": pretty_grammar(cnf),
        "steps": s1 + s2 + s3 + s4,
        "tokens": tokens
    }

# ============================================================
# RUN (STDIO por defecto)
# ============================================================

if __name__ == "__main__":
    # STDIO es el default; también puedes hacer mcp.run(transport="stdio")
    mcp.run()
