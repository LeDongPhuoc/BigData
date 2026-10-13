from backend.core.repository import Repository


class CompanyRepository(Repository):
    collection = "companies"

    def active(self, offset, limit):
        return self.listing({"status": "active"}, offset, limit)

    def employment(self, user_id, company_id):
        return self.query(
            "FOR e IN works_at FILTER e._from == @user AND e._to == @company RETURN e",
            user=user_id,
            company=company_id,
        )
