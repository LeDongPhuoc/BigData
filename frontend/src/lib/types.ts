import type { components } from "./api.generated";

type Schemas = components["schemas"];
// Pydantic serializes defaults in these responses; request fields may be optional.
export type Profile = Required<Schemas["Profile"]>;
export type User = Omit<Schemas["User"], "profile" | "privacy"> & {
  profile: Profile;
  privacy: Privacy;
};
export type Privacy = Required<Schemas["Privacy"]>;
export type Job = Required<Schemas["Job"]>;
export type JobPreview = Pick<
  Job,
  | "id"
  | "title"
  | "company_id"
  | "location"
  | "level"
  | "work_mode"
  | "salary_min"
  | "salary_max"
  | "source"
>;
export type Company = Schemas["Company"];
export type Skill = Schemas["Skill"];
export type Connection = Schemas["Connection"];
export type Referral = Schemas["Referral"];
export type Notification = Schemas["Notification"];
export type Tokens = Schemas["Tokens"];
export type UserSummary = Schemas["UserSummary"];
export type Path = Omit<
  Schemas["Path"],
  "explanation" | "edges" | "next_step"
> & {
  edges: { id: string; status: string; trust: number | null }[];
  next_step: { action: string; referrer_id: string; via_user_id: string };
  explanation: {
    mean_declared_trust: number;
    weights: { trust: number; reachability: number };
    ranking: string;
  };
};
export type PublicProfile = Omit<
  Schemas["PublicProfile"],
  "skills" | "employment" | "profile"
> & {
  profile: Profile;
  skills:
    | {
        id: string;
        name: string;
        proficiency: number;
        years_experience: number;
        verified: boolean;
      }[]
    | null;
  employment:
    { company_id: string; company_name: string; title: string }[] | null;
};
export type MatchResult = {
  job: JobPreview;
  score: number;
  eligible: boolean;
  explanation: {
    components: Record<string, number>;
    missing_required: string[];
    required_ratio: number;
    salary_overlap: boolean | null;
    requirements: {
      id: string;
      name: string;
      kind: "required" | "preferred";
      matched: boolean;
      importance: number;
    }[];
  };
};
export type Page<T> = {
  items: T[];
  offset: number;
  limit: number;
  has_more: boolean;
};
