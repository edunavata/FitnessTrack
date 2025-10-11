def is_owner(*, actor_id, owner_id) -> bool:
    """Return True if the actor owns the resource."""
    return str(actor_id) == str(owner_id)
