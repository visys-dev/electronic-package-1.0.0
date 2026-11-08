class Problem(Exception):
    def __init__(self, status: int, code: str, message: str, fields=None):
        self.status, self.code, self.message = status, code, message
        self.fields = fields or []


def require(
    condition, status=403, code="FORBIDDEN", message="Дія заборонена.", field=None
):
    if not condition:
        raise Problem(
            status,
            code,
            message,
            [{"field": field, "message": message}] if field else [],
        )
