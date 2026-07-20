"""PDF generation helpers."""

from __future__ import annotations

from app.models.cv import CV


def cv_to_html(cv: CV) -> str:
    """Render a simple HTML CV suitable for WeasyPrint or browser print."""
    def esc(text: str | None) -> str:
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

    sections = []
    if cv.summary:
        sections.append(f"<h2>Summary</h2><p>{esc(cv.summary)}</p>")
    if cv.experience:
        sections.append(f"<h2>Experience</h2><div>{esc(cv.experience)}</div>")
    if cv.education:
        sections.append(f"<h2>Education</h2><div>{esc(cv.education)}</div>")
    if cv.skills:
        sections.append(f"<h2>Skills</h2><p>{esc(cv.skills)}</p>")
    if cv.links:
        sections.append(f"<h2>Links</h2><p>{esc(cv.links)}</p>")

    contact_bits = [b for b in [cv.email, cv.phone, cv.location] if b]
    contact = " · ".join(esc(b) for b in contact_bits)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{esc(cv.full_name) or "CV"}</title>
  <style>
    body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; color: #222; }}
    h1 {{ margin-bottom: 0; }}
    h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 24px; }}
    .headline {{ color: #555; font-style: italic; margin-top: 4px; }}
    .contact {{ color: #666; margin-bottom: 24px; }}
  </style>
</head>
<body>
  <h1>{esc(cv.full_name) or "Untitled CV"}</h1>
  <p class="headline">{esc(cv.headline)}</p>
  <p class="contact">{contact}</p>
  {"".join(sections)}
</body>
</html>
"""


def generate_cv_pdf(cv: CV) -> bytes:
    """Generate PDF bytes from a CV model. Requires WeasyPrint system libs."""
    html = cv_to_html(cv)
    try:
        from weasyprint import HTML

        return HTML(string=html).write_pdf()
    except Exception as exc:  # noqa: BLE001 — surface friendly error upstream
        raise RuntimeError(
            "PDF generation failed. Install WeasyPrint system dependencies "
            f"or use the HTML endpoint instead. Detail: {exc}"
        ) from exc
