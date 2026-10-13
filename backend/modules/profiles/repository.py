from backend.core.repository import Repository
from database.migrate import utc_now


class ProfileRepository(Repository):
    collection = "users"

    def skills(self, user_id):
        return self.query(
            "FOR e IN has_skill FILTER e._from == @user "
            "LET s = DOCUMENT(e._to) FILTER s.status == 'active' "
            "SORT s.normalized_name RETURN {id:s._key,name:s.name,"
            "proficiency:e.proficiency,years_experience:e.years_experience,verified:e.verified}",
            user=user_id,
        )

    def employment(self, user_id):
        return self.query(
            "FOR e IN works_at FILTER e._from == @user AND e.status == 'current' "
            "AND e.verified AND e.start_at <= @now AND (e.end_at == null OR e.end_at > @now) "
            "LET c = DOCUMENT(e._to) FILTER c.status == 'active' "
            "SORT c.name RETURN {company_id:c._key,company_name:c.name,title:e.title}",
            user=user_id,
            now=utc_now(),
        )
