from backend.core.errors import missing
from backend.core.repository import Repository


class JobRepository(Repository):
    collection = "jobs"

    def company(self, job_id):
        rows = self.query(
            "FOR e IN job_at_company FILTER e._from == @job RETURN DOCUMENT(e._to)",
            job=job_id,
        )
        if len(rows) != 1 or rows[0] is None:
            raise missing()
        return rows[0]

    def requirements(self, job_id):
        return self.query(
            "FOR e IN job_requires_skill FILTER e._from == @job SORT e._to RETURN "
            "{skill_id:PARSE_IDENTIFIER(e._to).key,kind:e.kind,min_proficiency:e.min_proficiency,"
            "min_years:e.min_years,importance:e.importance}",
            job=job_id,
        )

    def browse(
        self, offset, limit, company_id=None, *, q="", location="", work_mode=None, level=None
    ):
        return self.query(
            "FOR j IN jobs FILTER j.status == 'open' "
            "AND (@mode == null OR j.work_mode == @mode) "
            "AND (@level == null OR j.level == @level) "
            "AND (@location == '' OR CONTAINS(LOWER(j.location), @location)) "
            "LET employer = FIRST(FOR e IN job_at_company FILTER e._from == j._id "
            "RETURN DOCUMENT(e._to)) FILTER employer != null AND employer.status == 'active' "
            "AND (@company == null OR employer._id == @company) "
            "AND (@q == '' OR CONTAINS(LOWER(j.title), @q) "
            "OR CONTAINS(LOWER(j.description), @q) OR CONTAINS(LOWER(employer.name), @q) "
            "OR LENGTH((FOR e IN job_requires_skill FILTER e._from == j._id "
            "LET skill = DOCUMENT(e._to) FILTER skill != null AND skill.status == 'active' "
            "AND CONTAINS(LOWER(skill.name), @q) LIMIT 1 RETURN 1)) > 0) "
            "SORT j.published_at DESC,j._key ASC LIMIT @offset,@count RETURN j",
            company=company_id,
            q=q,
            location=location,
            mode=work_mode,
            level=level,
            offset=offset,
            count=limit + 1,
        )
