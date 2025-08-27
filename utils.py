from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pysat.examples.hitman import Hitman
from pysat.examples.lbx import LBX
from pysat.examples.optux import OptUx
from pysat.examples.rc2 import RC2
from pysat.formula import CNF, WCNF, IDPool
from pysat.solvers import Solver

from scheduler import CourseScheduler


def get_vars(KB: List[List[int]]) -> Set[int]:
    """Extract all unique variables from a knowledge base.

    Parameters
    ----------
    KB : list of list of int
        Knowledge base represented as a list of clauses, where each clause
        is a list of literals (positive or negative integers).

    Returns
    -------
    set of int
        Set of all unique variable identifiers (absolute values of literals).
    """
    variables = set()
    for c in KB:
        for l in c:
            variables.add(abs(l))
    return variables


def map_explanation(explanation: List[List[int]], vpool: IDPool) -> List[Any]:
    """Map explanation indices to their corresponding objects using a variable pool.

    Parameters
    ----------
    explanation : list of list of int
        List of explanations where each explanation is a list of variable indices.
    vpool : IDPool
        Variable pool object that maps variable indices to their corresponding objects.

    Returns
    -------
    list
        List of mapped explanation objects, flattened from all sub-explanations.
    """
    mapped_explanation = []
    for e in explanation:
        sub_e = [vpool.obj(i) for i in e if i > 0 and vpool.obj(i)]
        mapped_explanation.extend(sub_e)
    return mapped_explanation


def get_MUS(
    public: Optional[List[List[int]]],
    private: Optional[List[List[int]]],
    q: CNF,
    vpool: IDPool,
) -> List[List[int]]:
    """Compute a minimal unsatisfiable set (MUS) from public and private knowledge bases.

    Parameters
    ----------
    public : list of list of int or None
        Public clauses to be added with weight 1.
    private : list of list of int or None
        Private clauses to be added with weight 100.
    q : CNF
        Query formula to be negated and added to the weighted CNF.
    vpool : IDPool
        Variable pool for managing variable indices.

    Returns
    -------
    list of list of int
        List of clauses forming the minimal unsatisfiable set.
    """
    # Compute a minimal unsatisfiable set
    wcnf2 = WCNF()
    if public:
        for c in public:
            wcnf2.append(c, weight=1)

    if private:
        for c in private:
            wcnf2.append(c, weight=100)

    wcnf2.extend((q.negate(topv=vpool.top).clauses))

    # wcnf2.extend(q)

    solver = OptUx(wcnf2)
    mus = solver.compute()
    expl = [list(wcnf2.soft[m - 1]) for m in mus]
    return expl
    return map_explanation(expl, vpool)


def get_MCS(
    public: Optional[List[List[int]]],
    private: Optional[List[List[int]]],
    q: CNF,
    vpool: IDPool,
) -> List[List[int]]:
    """Compute minimal correction set (MCS) using LBX algorithm.

    Parameters
    ----------
    public : list of list of int or None
        Public clauses to be added with weight 1.
    private : list of list of int or None
        Private clauses to be added with weight 100.
    q : CNF
        Query formula to be added to the weighted CNF.
    vpool : IDPool
        Variable pool for managing variable indices.

    Returns
    -------
    list of list of int
        List of clauses forming the minimal correction set.
    """
    # Compute minimal hitting set
    wcnf = WCNF()
    if public:
        for c in public:
            wcnf.append(c, weight=1)

    if private:
        for c in private:
            wcnf.append(c, weight=100)

    # wcnf.extend(q.negate(topv=vpool.top).clauses)
    wcnf.extend(q)

    lbx = LBX(wcnf, use_cld=True, solver_name="g3")
    # Compute mcs and return the clauses indexes
    mcs = lbx.compute()
    return [list(wcnf.soft[m - 1]) for m in mcs]


def create_lookup_dict(clasues: List[Any]) -> Tuple[defaultdict, defaultdict]:
    """Create bidirectional lookup dictionaries for clauses.

    Parameters
    ----------
    clasues : list
        List of clause labels or identifiers.

    Returns
    -------
    tuple of (defaultdict, defaultdict)
        A tuple containing:
        - idx_to_cls: Maps indices (1-based) to clause labels
        - cls_to_index: Maps clause labels to indices (1-based)
    """
    idx_to_cls = defaultdict()
    cls_to_index = defaultdict()

    for i, label in enumerate(clasues):
        idx_to_cls[i + 1] = label
        cls_to_index[label] = i + 1
    return idx_to_cls, cls_to_index


def get_clauses_from_index(
    seed: Optional[List[int]], clauses_dict: Dict[int, Any]
) -> List[Any]:
    """Retrieve clauses from indices using a lookup dictionary.

    Parameters
    ----------
    seed : list of int or None
        List of indices to look up in the clauses dictionary.
    clauses_dict : dict
        Dictionary mapping indices to clauses.

    Returns
    -------
    list
        List of clauses corresponding to the provided indices.
    """
    cls = []
    if seed:
        # seed = [item for sublist in seed for item in sublist]
        for s in seed:
            # print(s,'la')
            print("YO", clauses_dict[s])
            cls.extend(clauses_dict[s])
    return cls


def get_index_from_clauses(seed: List[int], clauses_dict: Dict[Any, Any]) -> List[int]:
    """Get indices corresponding to clauses using a reverse lookup dictionary.

    Parameters
    ----------
    seed : list
        List of clauses to find indices for.
    clauses_dict : dict
        Dictionary mapping indices/keys to clause values.

    Returns
    -------
    list of int
        List of indices corresponding to the input clauses.
    """
    idx = []
    for s in seed:
        for key, val in clauses_dict.items():
            if val == s:
                idx.append(key)
    return idx


def SAT(KB1: List[List[int]], KB2: List[List[int]]) -> bool:
    """Check satisfiability of combined knowledge bases.

    Parameters
    ----------
    KB1 : list of list of int
        First knowledge base as a list of clauses.
    KB2 : list of list of int
        Second knowledge base as a list of clauses.

    Returns
    -------
    bool
        True if the combined knowledge bases are satisfiable, False otherwise.
    """
    s = Solver(name="g4")
    for k in KB1 + KB2:
        s.add_clause(k)
    if s.solve():
        return True
    else:
        return False


def skeptical_entailment(
    scheduler: CourseScheduler, KB: List[List[int]], seed: List[List[int]], q: CNF
) -> bool:
    """Check if knowledge base skeptically entails a query.

    Parameters
    ----------
    scheduler : CourseScheduler
        Scheduler object containing variable pool information.
    KB : list of list of int
        Knowledge base as a list of clauses.
    seed : list of list of int
        Additional seed clauses.
    q : CNF
        Query formula to check entailment for.

    Returns
    -------
    bool
        True if KB skeptically entails the query, False otherwise.
    """
    # Check if KB entails a query
    s = Solver()
    for k in KB:
        s.add_clause(k)
    for k in seed:
        s.add_clause(k)
    # add negation of query

    s.append_formula(q.negate(topv=scheduler.vpool.top).clauses)
    if s.solve() == False:
        s.delete()
        return True
    else:
        return False


def getMCS(
    KB: List[List[int]],
    lits: List[List[int]],
    query: List[List[int]],
    seed: List[List[int]],
) -> List[List[int]]:
    """Compute minimal correction set using LBX algorithm.

    Parameters
    ----------
    KB : list of list of int
        Knowledge base as a list of clauses.
    lits : list of list of int
        Additional literals/clauses.
    query : list of list of int
        Query clauses to be added as hard constraints.
    seed : list of list of int
        Seed clauses to be added as hard constraints.

    Returns
    -------
    list of list of int
        Minimal correction set as a list of clauses, or [[]] if no MCS found.
    """

    wcnf = WCNF()

    # add seed as hard
    for s in seed:
        wcnf.append(s)

    # add query as hard
    wcnf.extend(query)

    # add remaining clauses as soft
    for k in KB:
        if k not in seed:
            wcnf.append(k, weight=1)
    for l in lits:
        wcnf.append(l, weight=0)

    lbx = LBX(wcnf, solver_name="g4", use_cld=True, use_timer=True)
    mcs = lbx.compute()
    # print('MCS oracle time: {0:.4f}'.format(lbx.oracle_time()))

    if mcs:
        return [list(wcnf.soft[m - 1]) for m in mcs]
    else:
        return [[]]


def getMCS_MaxSAT(
    scheduler: CourseScheduler,
    KB: List[List[int]],
    lits: List[List[int]],
    query: List[List[int]],
    seed: List[List[int]],
) -> List[List[int]]:
    """Compute minimal correction set using MaxSAT approach.

    Parameters
    ----------
    scheduler : CourseScheduler
        Scheduler object containing templates for constraint mapping.
    KB : list of list of int
        Knowledge base as a list of clauses.
    lits : list of list of int
        Additional literals/clauses.
    query : list of list of int
        Query clauses to be added as hard constraints.
    seed : list of list of int
        Seed clauses to be added as hard constraints.

    Returns
    -------
    list of list of int
        Minimal correction set based on scheduler templates.
    """
    wcnf = WCNF()

    # add seed as hard
    for s in seed:
        wcnf.append(s)

    # add query as hard
    wcnf.extend(query)

    for l in lits:
        wcnf.append(l)

    # add KB clauses as soft
    for k in KB:
        if k not in seed:
            wcnf.append(k, weight=5)

    RC = RC2(wcnf, solver="g4", adapt=True)
    model = RC.compute()

    mcs_KB = []
    for label in scheduler.templates:
        s = Solver("g3")
        s.append_formula(scheduler.templates[label])
        if not s.solve(assumptions=model):
            mcs_KB.extend(scheduler.templates[label])
            s.delete()
    return mcs_KB


def explanation(
    scheduler: Any, KB: List[List[int]], lits: List[List[int]], query: List[List[int]]
) -> Union[List[str], str]:
    """Generate explanation using hitting set enumeration.

    Parameters
    ----------
    scheduler : CourseScheduler
        Scheduler object containing constraint templates.
    KB : list of list of int
        Knowledge base as a list of clauses.
    lits : list of list of int
        Additional literals/clauses.
    query : list of list of int
        Query clauses to find explanation for.

    Returns
    -------
    list or str
        Template explanation labels if found, otherwise "No explanation".
    """

    # idx2cls, cls2idx = create_lookup_dict(scheduler.templates)

    blocked = []
    R = Hitman(htype="maxsat")  # Reconciliation formula
    # wcnf = WCNF()
    # for c in KB:
    #     wcnf.append(c, weight=1)
    # for l in lits:
    #     wcnf.append(l, weight=1)
    # for q in query:
    #     wcnf.append(q)
    # MCS = LBX(wcnf, solver_name='g3')

    while True:
        seed = R.get()
        e_plus = []
        template_expl = []
        if seed == None:
            return "No explanation"
        for s in seed:
            e_plus.extend(scheduler.templates[s])
            template_expl.append(s)

        # print(seed)
        if SAT(e_plus, []) and not SAT(e_plus + lits, query):
            # R.block(seed) # block the seed to generate a new explanation
            return template_expl
        else:
            mcs = getMCS(KB, lits, query, e_plus)
            # mcs = getMCS_MaxSAT(scheduler, KB, lits, query, e_plus)
            # Add all relevant clauses from scheduler to C
            if mcs != [[]]:
                relevant_clauses = add_relevant_clauses(scheduler, mcs)
                # C_indexed = []
                # for r in relevant_clauses:
                # C_indexed.append(cls2idx[r])
                R.hit(relevant_clauses)


def add_relevant_clauses(scheduler: CourseScheduler, C: List[List[int]]) -> List[str]:
    """Identify relevant template labels for given clauses.

    Parameters
    ----------
    scheduler : CourseScheduler
        Scheduler object containing constraint templates.
    C : list of list of int
        List of clauses to find relevant templates for.

    Returns
    -------
    list of str
        List of template labels that contain the given clauses.
    """
    relevant_clauses = []
    for c in C:
        for label in scheduler.templates:
            if c in scheduler.templates[label]:
                if label not in relevant_clauses:
                    relevant_clauses.append(label)
    return relevant_clauses


def repair(KB: List[List[int]], model: List[List[int]]) -> List[List[int]]:
    """Repair a knowledge base by removing conflicting clauses based on a model.

    Parameters
    ----------
    KB : list of list of int
        Knowledge base as a list of clauses.
    model : list of list of int
        Model constraints to be satisfied.

    Returns
    -------
    list of list of int
        Repaired knowledge base with conflicting clauses removed and model added.
    """
    wcnf = WCNF()
    for c in KB:
        wcnf.append(c, weight=1)
    wcnf.extend(model)
    MCS = LBX(wcnf, solver_name="CryptoMinisat")
    mcs = MCS.compute()
    mcs_clauses = [list(wcnf.soft[m - 1]) for m in mcs]
    new_KB = [c for c in KB if c not in mcs_clauses]
    new_KB.extend(model)
    return new_KB
