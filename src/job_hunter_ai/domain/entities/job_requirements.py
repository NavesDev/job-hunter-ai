from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JobRequirements:
    """What a posting asks for, split the way an ATS ranks it.

    `required` carries the must-haves and `preferred` the nice-to-haves; they are weighted
    differently (docs/scoring.md). `months_of_experience` is `None` when the posting asks
    for none — an absent requirement is never a failed one.
    """

    title: str = ""
    required: tuple[str, ...] = ()
    preferred: tuple[str, ...] = ()
    months_of_experience: int | None = None
