"""Rule-based CV text extraction and skill/title parsing (Phase 1 — no AI)."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

# Common tech skills / tools (lowercase keys, display labels)
SKILL_CATALOG: dict[str, str] = {
    # Languages
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "c++": "C++",
    "c#": "C#",
    "csharp": "C#",
    "ruby": "Ruby",
    "php": "PHP",
    "scala": "Scala",
    "r": "R",
    "matlab": "MATLAB",
    "sql": "SQL",
    "bash": "Bash",
    "shell": "Shell",
    # Web / frontend
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "vue": "Vue",
    "vue.js": "Vue",
    "angular": "Angular",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "svelte": "Svelte",
    "html": "HTML",
    "css": "CSS",
    "tailwind": "Tailwind",
    "sass": "Sass",
    "redux": "Redux",
    # Backend / frameworks
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "express": "Express",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "nestjs": "NestJS",
    "spring": "Spring",
    "spring boot": "Spring Boot",
    ".net": ".NET",
    "dotnet": ".NET",
    "rails": "Rails",
    "laravel": "Laravel",
    "graphql": "GraphQL",
    "rest": "REST",
    "rest api": "REST API",
    # Data / ML
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "keras": "Keras",
    "spark": "Spark",
    "hadoop": "Hadoop",
    "airflow": "Airflow",
    "dbt": "dbt",
    "etl": "ETL",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "computer vision": "Computer Vision",
    "data analysis": "Data Analysis",
    "data science": "Data Science",
    "data engineering": "Data Engineering",
    # Cloud / devops
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "google cloud": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "jenkins": "Jenkins",
    "ci/cd": "CI/CD",
    "github actions": "GitHub Actions",
    "gitlab": "GitLab",
    "linux": "Linux",
    "nginx": "Nginx",
    # Databases
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "dynamodb": "DynamoDB",
    "sqlite": "SQLite",
    "cassandra": "Cassandra",
    "snowflake": "Snowflake",
    "bigquery": "BigQuery",
    # Other
    "git": "Git",
    "linux": "Linux",
    "agile": "Agile",
    "scrum": "Scrum",
    "jira": "Jira",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "celery": "Celery",
    "microservices": "Microservices",
    "api design": "API Design",
    "system design": "System Design",
    "testing": "Testing",
    "pytest": "pytest",
    "jest": "Jest",
    "playwright": "Playwright",
    "selenium": "Selenium",
    "figma": "Figma",
    "ui/ux": "UI/UX",
    "product management": "Product Management",
    "project management": "Project Management",
}

# Job-title patterns (regex → canonical label)
TITLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(senior|sr\.?)\s+(software|backend|frontend|full[\s-]?stack)\s+(engineer|developer)\b", re.I), "Senior Software Engineer"),
    (re.compile(r"\b(software|backend|frontend|full[\s-]?stack)\s+(engineer|developer)\b", re.I), "Software Engineer"),
    (re.compile(r"\b(data\s+engineer)\b", re.I), "Data Engineer"),
    (re.compile(r"\b(data\s+scientist)\b", re.I), "Data Scientist"),
    (re.compile(r"\b(data\s+analyst)\b", re.I), "Data Analyst"),
    (re.compile(r"\b(machine\s+learning\s+engineer|ml\s+engineer)\b", re.I), "ML Engineer"),
    (re.compile(r"\b(devops\s+engineer)\b", re.I), "DevOps Engineer"),
    (re.compile(r"\b(sre|site\s+reliability\s+engineer)\b", re.I), "SRE"),
    (re.compile(r"\b(cloud\s+engineer)\b", re.I), "Cloud Engineer"),
    (re.compile(r"\b(product\s+manager)\b", re.I), "Product Manager"),
    (re.compile(r"\b(project\s+manager)\b", re.I), "Project Manager"),
    (re.compile(r"\b(qa\s+engineer|quality\s+assurance)\b", re.I), "QA Engineer"),
    (re.compile(r"\b(mobile\s+(engineer|developer)|ios\s+developer|android\s+developer)\b", re.I), "Mobile Developer"),
    (re.compile(r"\b(engineering\s+manager)\b", re.I), "Engineering Manager"),
    (re.compile(r"\b(tech(?:nical)?\s+lead|team\s+lead)\b", re.I), "Tech Lead"),
]


@dataclass
class ParsedCV:
    raw_text: str
    skills: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    email: str | None = None
    phone: str | None = None
    suggested_headline: str | None = None


def extract_text_from_bytes(filename: str, content: bytes) -> str:
    """Extract plain text from PDF, DOCX, or plain text uploads."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf(content)
    if name.endswith(".docx"):
        return _extract_docx(content)
    if name.endswith((".txt", ".md", ".rtf")):
        return content.decode("utf-8", errors="ignore")
    # Try PDF then text fallback
    try:
        text = _extract_pdf(content)
        if text.strip():
            return text
    except Exception:  # noqa: BLE001
        pass
    return content.decode("utf-8", errors="ignore")


def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF upload. pip install pypdf") from exc

    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            continue
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("Could not extract text from PDF (may be scanned/image-only)")
    return text


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("python-docx is required for DOCX upload. pip install python-docx") from exc

    doc = Document(io.BytesIO(content))
    parts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    # tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text and cell.text.strip():
                    parts.append(cell.text.strip())
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("Could not extract text from DOCX")
    return text


def parse_cv_text(text: str) -> ParsedCV:
    """Heuristic parse: skills from catalog, titles from patterns, basic contact."""
    if not text or not text.strip():
        return ParsedCV(raw_text=text or "")

    normalized = _normalize(text)
    skills = _extract_skills(normalized, text)
    titles = _extract_titles(text)
    email = _extract_email(text)
    phone = _extract_phone(text)
    keywords = _extra_keywords(normalized, skills)

    return ParsedCV(
        raw_text=text,
        skills=skills,
        titles=titles,
        keywords=keywords,
        email=email,
        phone=phone,
        suggested_headline=titles[0] if titles else (skills[0] if skills else None),
    )


def cv_profile_text(cv) -> str:
    """Combine structured CV fields + raw upload text for parsing/matching."""
    parts = [
        cv.full_name,
        cv.headline,
        cv.summary,
        cv.experience,
        cv.education,
        cv.skills,
        cv.links,
        cv.raw_text,
        cv.parsed_skills,
        cv.parsed_titles,
    ]
    return "\n".join(p for p in parts if p)


def _normalize(text: str) -> str:
    t = text.lower()
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[/|•·,;()\[\]{}]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _extract_skills(normalized: str, original: str) -> list[str]:
    found: dict[str, str] = {}  # label -> label (dedupe)

    # Prefer longer phrases first
    items = sorted(SKILL_CATALOG.items(), key=lambda kv: len(kv[0]), reverse=True)
    for key, label in items:
        if " " in key or "." in key or "/" in key or "+" in key or "#" in key:
            if key in normalized:
                found[label] = label
        else:
            # word boundary for short tokens (avoid "go" in "golang" handled separately)
            if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", normalized):
                found[label] = label

    # Skills section heuristic: lines under a "Skills" heading
    section = _section_after(original, r"skills|technical skills|tech stack|technologies")
    if section:
        for chunk in re.split(r"[,|/•\n;]+", section):
            token = chunk.strip().lower()
            if not token or len(token) > 40:
                continue
            if token in SKILL_CATALOG:
                found[SKILL_CATALOG[token]] = SKILL_CATALOG[token]

    return list(found.values())


def _extract_titles(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for pattern, label in TITLE_PATTERNS:
        if pattern.search(text) and label not in seen:
            found.append(label)
            seen.add(label)
    return found


def _extract_email(text: str) -> str | None:
    m = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    return m.group(0) if m else None


def _extract_phone(text: str) -> str | None:
    m = re.search(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}", text)
    if not m:
        return None
    candidate = m.group(0).strip()
    digits = re.sub(r"\D", "", candidate)
    if len(digits) < 7:
        return None
    return candidate


def _extra_keywords(normalized: str, skills: list[str]) -> list[str]:
    """A few high-signal non-skill tokens for matching."""
    extras = []
    for phrase in (
        "remote",
        "backend",
        "frontend",
        "full stack",
        "fullstack",
        "api",
        "microservices",
        "distributed systems",
        "cloud",
        "security",
        "fintech",
        "healthcare",
        "saas",
    ):
        if phrase in normalized:
            extras.append(phrase.title() if phrase != "api" else "API")
    skill_set = {s.lower() for s in skills}
    return [e for e in extras if e.lower() not in skill_set][:12]


def _section_after(text: str, heading_re: str, max_chars: int = 800) -> str:
    m = re.search(rf"(?im)^(?:{heading_re})\s*:?\s*$", text)
    if not m:
        m = re.search(rf"(?i)(?:{heading_re})\s*[:\-]", text)
    if not m:
        return ""
    start = m.end()
    # stop at next all-caps-ish heading line
    rest = text[start : start + max_chars]
    stop = re.search(r"(?m)^[A-Z][A-Za-z ]{2,30}$", rest[20:] if len(rest) > 20 else "")
    if stop:
        return rest[: stop.start() + 20]
    return rest
