import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def generate_company_policy_pdf():
    pdf_path = SAMPLE_DIR / "Company_Policy.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        spaceAfter=14
    )
    heading_style = ParagraphStyle(
        'DocHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=10
    )

    # Page 1: Overview & Working Hours
    story.append(Paragraph("ACME GLOBAL TECHNOLOGIES - CORPORATE POLICIES", title_style))
    story.append(Paragraph("Document Reference: POL-2026-V1.4", body_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Section 1: Working Hours and Flexibility", heading_style))
    story.append(Paragraph(
        "Standard business operating hours for Acme Global Technologies are 9:00 AM to 5:30 PM, Monday through Friday. "
        "Employees are expected to be available for core collaboration between 10:00 AM and 4:00 PM local time. "
        "Flexible working arrangements, including staggered starting hours, may be agreed upon with direct management approval.",
        body_style
    ))
    story.append(PageBreak())

    # Page 2: Remote Work Policy
    story.append(Paragraph("Section 2: Hybrid and Remote Work Guidelines", heading_style))
    story.append(Paragraph(
        "All full-time staff members are eligible for hybrid work, permitting up to three days per week of remote work from an approved home location. "
        "Remote workstations must maintain secure Wi-Fi connections adhering to Corporate Security Guidelines. "
        "Employees traveling abroad must obtain prior written approval from Human Resources and Information Security before accessing company repositories.",
        body_style
    ))
    story.append(PageBreak())

    # Page 3: Annual Leave Policy
    story.append(Paragraph("Section 3: Annual Leave & Time Off Policy", heading_style))
    story.append(Paragraph(
        "All standard full-time permanent employees are entitled to 20 days of annual leave per calendar year. "
        "Annual leave accrues at the rate of 1.67 days for each completed month of service. "
        "A maximum of 5 unused annual leave days may be carried over into the following calendar year, provided they are utilized by March 31st.",
        body_style
    ))
    story.append(Paragraph(
        "Leave requests exceeding three consecutive days must be submitted via the Employee HR Portal at least two weeks in advance. "
        "Statutory public holidays are observed in addition to standard annual leave entitlement.",
        body_style
    ))
    story.append(PageBreak())

    # Page 4: Professional Conduct
    story.append(Paragraph("Section 4: Professional Conduct and Ethical Standards", heading_style))
    story.append(Paragraph(
        "Acme Global Technologies promotes an inclusive, respectful, and safe workplace for all colleagues. "
        "Discrimination, harassment, or retaliation of any form will result in disciplinary action up to and including immediate termination. "
        "Conflicts of interest must be disclosed promptly to the compliance committee.",
        body_style
    ))

    doc.build(story)
    print(f"Generated: {pdf_path}")

def generate_employee_handbook_md():
    md_path = SAMPLE_DIR / "Employee_Handbook.md"
    content = """# ACME GLOBAL TECHNOLOGIES - EMPLOYEE HANDBOOK

## 1. Welcome to Acme Global
Welcome to the team! This handbook summarizes operational workflows, team expectations, and core organizational principles.

## 2. Onboarding & Equipment
Every new team member receives a standardized company-issued laptop, security token, and access credentials during Week 1. Personal laptops are strictly prohibited from storing source code or sensitive databases without Enterprise Mobile Device Management (MDM).

## 3. Grievance and Whistleblowing Procedure
If an employee encounters workplace misconduct, safety hazards, or ethical breaches:
1. Speak with your immediate manager or People Partner.
2. If the issue involves management, contact ethics@acmeglobal.example.com.
3. Acme maintains an anonymous reporting hotline operated 24/7 by an independent compliance ombudsman.
Retaliation against any individual reporting in good faith is strictly prohibited.

## 4. Performance Reviews & Growth
Performance evaluations occur twice yearly, in June and December. Promotions and salary adjustments are benchmarked against industry peer percentiles.
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {md_path}")

def generate_leave_policy_txt():
    txt_path = SAMPLE_DIR / "Leave_Policy.txt"
    content = """ACME GLOBAL TECHNOLOGIES - DETAILED LEAVE POLICY

1. Annual Vacation Leave:
Full-time personnel receive 20 days of paid annual vacation each year. New hires accrue leave pro-rata.

2. Sick & Medical Leave:
Employees are granted 10 days of paid sick leave annually for personal illness or caring for immediate family members.
Absences exceeding three consecutive business days require a signed doctor's certificate.

3. Parental Leave:
Primary caregivers are eligible for 16 weeks of fully paid parental leave following the birth or adoption of a child.
Secondary caregivers receive 6 weeks of fully paid parental leave.

4. Bereavement Leave:
Employees are eligible for up to 5 consecutive paid days off in the event of the loss of an immediate family member.

5. Emergency Unpaid Leave:
In unforeseen crises, up to 30 days of unpaid personal leave may be granted subject to Department Head authorization.
"""
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {txt_path}")

def generate_security_policy_md():
    md_path = SAMPLE_DIR / "Security_Policy.md"
    content = """# ACME GLOBAL INFORMATION SECURITY POLICY

## 1. Password and Authentication Requirements
- All user passwords must contain at least 12 characters, including uppercase letters, lowercase letters, numbers, and symbols.
- Passwords must be updated every 90 days.
- Multi-Factor Authentication (MFA) via hardware security key or authenticator app is mandatory for all internal corporate accounts. SMS verification is prohibited.

## 2. Data Classification
- Public: Information intended for general public release.
- Internal: Standard business communications, memos, and non-sensitive project notes.
- Confidential: Proprietary algorithms, customer records, and employee salary data.
- Restricted: Cryptographic keys, credentials, and forensic audit logs.

## 3. Clean Desk Policy
Employees must lock their workstations whenever leaving their desks. Physical documents containing confidential data must be shredded or stored in locked filing cabinets when unattended.

## 4. Incident Reporting
Any suspected security breach, phishing email, or malware detection must be reported immediately to security-ops@acmeglobal.example.com within 30 minutes of discovery.
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {md_path}")

def generate_benefits_guide_txt():
    txt_path = SAMPLE_DIR / "Benefits_Guide.txt"
    content = """ACME GLOBAL TECHNOLOGIES - EMPLOYEE BENEFITS GUIDE

1. Health & Medical Coverage:
Comprehensive health, dental, and vision insurance is provided to all employees and eligible dependents.
The company covers 90% of employee premiums and 75% of dependent premiums.

2. Retirement Plan (401k):
Employees can contribute to the company 401(k) retirement plan upon their first day of employment.
Acme matches 100% of employee contributions up to 4% of base salary. Matching funds vest immediately.

3. Wellness & Gym Stipend:
Each employee receives a wellness stipend of $75 per month ($900 annually) for fitness memberships, mental health apps, or sports equipment.

4. Learning & Development Allowance:
Every staff member has an annual budget of $1,500 dedicated to professional certifications, books, and conference attendances.
"""
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {txt_path}")

if __name__ == "__main__":
    generate_company_policy_pdf()
    generate_employee_handbook_md()
    generate_leave_policy_txt()
    generate_security_policy_md()
    generate_benefits_guide_txt()
    print("All sample documents generated successfully.")
