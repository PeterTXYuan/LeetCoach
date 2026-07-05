def get_primary_approach_hints(problem):
    approach = next(
        approach for approach in problem["approaches"] if approach["isPrimary"]
    )

    return approach["id"], list(approach["hints"])


def get_approach_hints(problem, approach_id):
    approach = next(
        (
            approach
            for approach in problem["approaches"]
            if approach["id"] == approach_id
        ),
        None,
    )

    if approach is None:
        raise KeyError(approach_id)

    return list(approach["hints"])
