class NotFoundError(Exception):
    def __init__(self, entity: str):
        super().__init__(f"{entity} not found")


class ConflictError(Exception):
    pass