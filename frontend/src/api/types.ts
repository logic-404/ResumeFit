export type Status =
  | "draft"
  | "applied"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface SkillEntry {
  name: string;
  category?: string | null;
  proficiency?: string | null;
}

export interface ExperienceEntry {
  company: string;
  role: string;
  start_date?: string | null;
  end_date?: string | null;
  location?: string | null;
  bullets: string[];
}

export interface EducationEntry {
  institution: string;
  degree?: string | null;
  start?: string | null;
  end?: string | null;
  details?: string | null;
}

export interface FileStructureEntry {
  path: string;
  role: string;
}

export interface FileStructure {
  root_file: string;
  files: FileStructureEntry[];
}

export interface Profile {
  id: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  linkedin_url?: string | null;
  skills: SkillEntry[];
  experience: ExperienceEntry[];
  education: EducationEntry[];
  certifications: string[];
  source_format: "pdf" | "tex" | "tex_project";
  file_structure?: FileStructure | null;
  created_at: string;
  updated_at: string;
}

export interface ParsedJD {
  role: string;
  company: string;
  department?: string | null;
  experience_level: "junior" | "mid" | "senior" | "lead" | "principal";
  experience_years_min?: number | null;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  benefits: string[];
  location?: string | null;
  salary_range?: string | null;
}

export interface SkillMatch { skill: string; evidence: string }
export interface SkillGap { skill: string; severity: "required" | "preferred"; suggestion: string }
export interface TransferableSkill { skill: string; maps_to: string; explanation: string }

export interface GapAnalysis {
  matched_skills: SkillMatch[];
  missing_skills: SkillGap[];
  transferable_skills: TransferableSkill[];
  overall_match_score: number;
  recommendation: string;
}

export interface CoverLetter {
  greeting: string;
  opening_paragraph: string;
  body_paragraphs: string[];
  closing_paragraph: string;
  sign_off: string;
  tone_score: number;
  keyword_match_count: number;
}

export interface ChangeLogEntry { section: string; change: string; reason: string }

export interface PdfSourceResume {
  format: "pdf_source";
  sections: { title: string; bullets: string[] }[];
  plain_text: string;
  markdown: string;
  change_log: ChangeLogEntry[];
}

export interface TexResume {
  format: "tex";
  full_tex: string;
  change_log: ChangeLogEntry[];
}

export interface TexProjectResume {
  format: "tex_project";
  root_file: string;
  files: { path: string; content: string }[];
  change_log: ChangeLogEntry[];
}

export type TailoredResume = PdfSourceResume | TexResume | TexProjectResume;

export interface ApplicationSummary {
  id: string;
  company_name: string;
  role_title: string;
  location?: string | null;
  status: Status;
  applied_date?: string | null;
  response_date?: string | null;
  job_url?: string | null;
  created_at: string;
  updated_at: string;
  overall_match_score?: number | null;
}

export interface GeneratedOutputDTO {
  output_type: "cover_letter" | "gap_analysis" | "tailored_resume";
  version: number;
  content: any;
  model_used?: string | null;
  created_at: string;
}

export interface ApplicationDetail extends ApplicationSummary {
  raw_jd_text: string;
  parsed_jd: ParsedJD;
  salary_range?: string | null;
  notes?: string | null;
  outputs: GeneratedOutputDTO[];
}

export interface DashboardStats {
  total_applications: number;
  by_status: Record<Status, number>;
  response_rate: number;
  average_days_to_response?: number | null;
  top_matched_skills: string[];
  top_missing_skills: string[];
  applications_this_week: number;
  applications_this_month: number;
}

export interface AnalyseResponse { job_id: string }

export type StreamEvent =
  | { event: "step"; data: { name: string; status: "started" | "done"; ms?: number } }
  | { event: "result"; data: any }
  | { event: "error"; data: { code: string; message: string } };
