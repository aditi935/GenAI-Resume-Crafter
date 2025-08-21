import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from io import BytesIO
import re
import textwrap
from docx import Document
from docx.shared import Pt

load_dotenv()

def init_session_state():
    if 'resume_data' not in st.session_state:
        st.session_state.resume_data = {
            'contact_info': {
                'name': '',
                'email': '',
                'phone': '',
                'location': '',
                'linkedin': ''
            },
            'target_role': '',
            'professional_summary': '',
            'work_experience': [],
            'education': [],
            'skills': {
                'Technical': [],
                'Soft': []
            },
            'projects': [],
            'certifications': []
        }
    if 'use_default_data' not in st.session_state:
        st.session_state.use_default_data = False
    if 'job_description' not in st.session_state:
        st.session_state.job_description = ""
    if 'company_name' not in st.session_state:
        st.session_state.company_name = ""
    if 'optimized_resume' not in st.session_state:
        st.session_state.optimized_resume = None
    if 'cover_letter' not in st.session_state:
        st.session_state.cover_letter = ""
    if 'cover_letter_ats' not in st.session_state:
        st.session_state.cover_letter_ats = ""
    if 'ats_report' not in st.session_state:
        st.session_state.ats_report = ""
    if 'interview_prep' not in st.session_state:
        st.session_state.interview_prep = ""
    if 'show_comparison' not in st.session_state:
        st.session_state.show_comparison = False
    if 'selected_sections' not in st.session_state:
        st.session_state.selected_sections = [
            "Professional Summary", 
            "Work Experience", 
            "Education", 
            "Skills"
        ]
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Resume Builder"
    if 'api_key_valid' not in st.session_state:
        st.session_state.api_key_valid = False
    if 'user_api_key' not in st.session_state:
        st.session_state.user_api_key = ""
    if 'show_api_instructions' not in st.session_state:
        st.session_state.show_api_instructions = False
    if 'model' not in st.session_state:
        st.session_state.model = None
    if 'auto_optimize' not in st.session_state:
        st.session_state.auto_optimize = False

def configure_api(api_key):
    """Configure the API and check if it's valid"""
    try:
        genai.configure(api_key=api_key)
        genai.list_models()
        st.session_state.api_key_valid = True
        st.session_state.model = genai.GenerativeModel('gemini-1.5-flash')
        return True, "API key is valid"
    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "limit" in error_msg:
            return False, "API quota exceeded - please check your Google AI Studio quota"
        elif "invalid" in error_msg or "malformed" in error_msg:
            return False, "Invalid API key"
        else:
            return False, f"API error: {str(e)}"

def check_api_key():
    """Check if we have a valid API key from env or user input"""
    env_api_key = os.getenv("GOOGLE_API_KEY")
    if env_api_key:
        valid, message = configure_api(env_api_key)
        if valid:
            return True
        else:
            st.session_state.show_api_instructions = True
            return False
    return False

def show_api_key_input_in_sidebar():
    """Show API key input in sidebar"""
    st.markdown("---")
    st.subheader("🔑 API Configuration")
    
    with st.expander("How to Get Google API Key", expanded=False):
        st.markdown("""
        **Follow these steps to get your Google API Key:**
        1. Go to [Google AI Studio](https://aistudio.google.com/welcome)
        2. Signup/Signin with your google account
        3. Click on "Get API Key" in the navbar
        4. Create a new API key or copy an existing one
        5. Paste it in the field below
        """)
    
    api_key = st.text_input(
        "Enter your Google API Key and press Enter",
        type="password",
        value=st.session_state.user_api_key,
        key="sidebar_api_key_input",
        help="Required for AI-powered resume optimization"
    )
    
    if api_key and api_key != st.session_state.user_api_key:
        st.session_state.user_api_key = api_key
        valid, message = configure_api(api_key)
        if valid:
            st.session_state.show_api_instructions = False
            st.session_state.auto_optimize = True
        else:
            st.error(message)
    
    else:
        if st.session_state.user_api_key:
            st.info("API key not configured - Refresh the page again")
def create_resume_pdf(resume_data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    styles['Title'].textColor = colors.HexColor("#2E5D9E")
    styles['Title'].fontName = 'Helvetica-Bold'
    
    
    custom_styles = {
        'ResumeHeader': ParagraphStyle(
            name='ResumeHeader',
            parent=styles['Title'],
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=6
        ),
        'ResumeContact': ParagraphStyle(
            name='ResumeContact',
            parent=styles['BodyText'],
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=16,
            textColor=colors.HexColor("#444444")
        ),
        'ResumeRole': ParagraphStyle(
            name='ResumeRole',
            parent=styles['BodyText'],
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=16,
            textColor=colors.HexColor("#2E5D9E"),
            fontName='Helvetica-Bold'
        ),
        'ResumeSection': ParagraphStyle(
            name='ResumeSection',
            parent=styles['Heading2'],
            fontSize=12,
            leading=14,
            spaceAfter=6,
            textColor=colors.HexColor("#2E5D9E"),
            underlineWidth=1,
            underlineColor=colors.HexColor("#2E5D9E"),
            underlineOffset=-4,
            underlineGap=2
        ),
        'ResumeJobTitle': ParagraphStyle(
            name='ResumeJobTitle',
            parent=styles['BodyText'],
            fontSize=11,
            leading=13,
            spaceAfter=2,
            fontName='Helvetica-Bold'
        ),
        'ResumeCompany': ParagraphStyle(
            name='ResumeCompany',
            parent=styles['BodyText'],
            fontSize=10,
            leading=12,
            spaceAfter=4,
            textColor=colors.HexColor("#555555"),
            fontName='Helvetica-Oblique'
        ),
        'ResumeBullet': ParagraphStyle(
            name='ResumeBullet',
            parent=styles['BodyText'],
            leftIndent=10,
            spaceAfter=4,
            bulletFontName='Helvetica',
            bulletFontSize=10
        )
    }
    
    for style_name, style in custom_styles.items():
        styles.add(style)
    
    story = []
    
    
    story.append(Paragraph(resume_data['contact_info']['name'].upper(), styles['ResumeHeader']))
    
    
    contact_parts = []
    if 'email' in resume_data['contact_info']:
        contact_parts.append(f"✉ {resume_data['contact_info']['email']}")
    if 'phone' in resume_data['contact_info']:
        contact_parts.append(f"📞 {resume_data['contact_info']['phone']}")
    if 'location' in resume_data['contact_info']:
        contact_parts.append(f"📍 {resume_data['contact_info']['location']}")
    if 'linkedin' in resume_data['contact_info']:
        contact_parts.append(f"🔗 {resume_data['contact_info']['linkedin']}")
    
    story.append(Paragraph(" | ".join(contact_parts), styles['ResumeContact']))
    story.append(Paragraph(resume_data['target_role'].upper(), styles['ResumeRole']))
    story.append(Spacer(1, 1))
    story.append(Paragraph("<hr/>", styles['Normal']))
    story.append(Spacer(1, 12))
    
    
    story.append(Paragraph("PROFESSIONAL SUMMARY", styles['ResumeSection']))
    story.append(Paragraph(resume_data['professional_summary'], styles['Normal']))
    story.append(Spacer(1, 12))
    

    
    
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", styles['ResumeSection']))
    for exp in resume_data['professional_experience']:
        story.append(Paragraph(exp['job_title'], styles['ResumeJobTitle']))
        
        company_info = []
        if 'company' in exp:
            company_info.append(f"<b>{exp['company']}</b>")
        if 'dates' in exp:
            company_info.append(exp['dates'])
        if 'location' in exp:
            company_info.append(exp['location'])
        
        story.append(Paragraph(" | ".join(company_info), styles['ResumeCompany']))
        
        bullet_points = []
        for achievement in exp['achievements']:
            bullet_points.append(
                ListItem(
                    Paragraph(achievement, styles['ResumeBullet']),
                    bulletColor=colors.HexColor("#2E5D9E"),
                    value="•",
                    leftIndent=15
                )
            )
        
        story.append(ListFlowable(bullet_points, bulletType='bullet', leftIndent=20))
        story.append(Spacer(1, 8))
    
    
    story.append(Paragraph("EDUCATION", styles['ResumeSection']))
    for edu in resume_data['education']:
        edu_info = []
        if 'degree' in edu:
            edu_info.append(f"<b>{edu['degree']}</b>")
        if 'institution' in edu:
            edu_info.append(edu['institution'])
        if 'year' in edu:
            edu_info.append(f"({edu['year']})")
        if 'honors' in edu and edu['honors']:
            edu_info.append(f"<i>{edu['honors']}</i>")
        
        story.append(Paragraph(", ".join(edu_info), styles['Normal']))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))
    
    
    if 'technical_skills' in resume_data and resume_data['technical_skills']:
        story.append(Paragraph("TECHNICAL SKILLS", styles['ResumeSection']))
        
        skills = resume_data['technical_skills']
        skill_data = []
        for i in range(0, len(skills), 3):
            row = skills[i:i+3]
            while len(row) < 3:
                row.append("")
            skill_data.append(row)
        
        skill_table = Table(skill_data, colWidths=[doc.width/3]*3)
        skill_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(skill_table)
        story.append(Spacer(1, 12))
    
    
    if 'certifications' in resume_data and resume_data['certifications']:
        story.append(Paragraph("CERTIFICATIONS", styles['ResumeSection']))
        for cert in resume_data['certifications']:
            story.append(Paragraph(f"• {cert}", styles['Normal']))
        story.append(Spacer(1, 12))
    
    
    if 'projects' in resume_data and resume_data['projects']:
        story.append(Paragraph("PROJECTS", styles['ResumeSection']))
        for proj in resume_data['projects']:
            story.append(Paragraph(f"<b>{proj['name']}</b>", styles['ResumeJobTitle']))
            story.append(Paragraph(proj['description'], styles['Normal']))
            story.append(Paragraph(f"<font color='#555555'><i>Technologies: {', '.join(proj['technologies'])}</i></font>", styles['Normal']))
            story.append(Spacer(1, 8))
    
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("<font color='#888888' size=8>Generated by AI Job Search Assistant</font>", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_pdf_document(resume_data, is_resume=True):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    custom_styles = {
        'Header': ParagraphStyle(
            name='Header',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#2E5D9E"),
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=12
        ),
        'SectionHeader': ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#2E5D9E"),
            fontName='Helvetica-Bold',
            underlineWidth=1,
            underlineColor=colors.HexColor("#2E5D9E"),
            spaceAfter=6
        ),
        'JobTitle': ParagraphStyle(
            name='JobTitle',
            parent=styles['BodyText'],
            fontSize=11,
            leading=13,
            fontName='Helvetica-Bold',
            spaceAfter=2
        ),
        'Company': ParagraphStyle(
            name='Company',
            parent=styles['BodyText'],
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#555555"),
            fontName='Helvetica-Oblique',
            spaceAfter=4
        ),
        'BulletPoint': ParagraphStyle(
            name='BulletPoint',
            parent=styles['BodyText'],
            fontSize=10,
            leading=12,
            leftIndent=10,
            spaceAfter=4,
            bulletFontName='Helvetica',
            bulletFontSize=10
        ),
        'CoverBody': ParagraphStyle(
            name='CoverBody',
            parent=styles['BodyText'],
            fontSize=11,
            leading=14,
            spaceAfter=12
        ),
        'SkillCategory': ParagraphStyle(
            name='SkillCategory',
            parent=styles['BodyText'],
            fontSize=10,
            leading=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor("#2E5D9E"),
            spaceAfter=4
        )
    }
    for style_name, style in custom_styles.items():
        styles.add(style)
    
    elements = []
    
    if is_resume:
        if 'contact_info' in resume_data and 'name' in resume_data['contact_info'] and resume_data['contact_info']['name']:
            elements.append(Paragraph(resume_data['contact_info']['name'].upper(), styles['Header']))
            
            contact_parts = []
            if 'email' in resume_data['contact_info'] and resume_data['contact_info']['email']:
                contact_parts.append(f"✉ {resume_data['contact_info']['email']}")
            if 'phone' in resume_data['contact_info'] and resume_data['contact_info']['phone']:
                contact_parts.append(f"📞 {resume_data['contact_info']['phone']}")
            if 'location' in resume_data['contact_info'] and resume_data['contact_info']['location']:
                contact_parts.append(f"📍 {resume_data['contact_info']['location']}")
            if 'linkedin' in resume_data['contact_info'] and resume_data['contact_info']['linkedin']:
                contact_parts.append(f"🔗 {resume_data['contact_info']['linkedin']}")
            
            if contact_parts:
                elements.append(Paragraph(" | ".join(contact_parts), styles['BodyText']))
                elements.append(Spacer(1, 12))
        
        if 'professional_summary' in resume_data and resume_data['professional_summary']:
            elements.append(Paragraph("PROFESSIONAL SUMMARY", styles['SectionHeader']))
            elements.append(Paragraph(resume_data['professional_summary'], styles['BodyText']))
            elements.append(Spacer(1, 12))
        
        if 'work_experience' in resume_data and resume_data['work_experience']:
            elements.append(Paragraph("PROFESSIONAL EXPERIENCE", styles['SectionHeader']))
            for exp in resume_data['work_experience']:
                if 'job_title' in exp and exp['job_title']:
                    elements.append(Paragraph(exp['job_title'], styles['JobTitle']))
                
                company_info = []
                if 'company' in exp and exp['company']:
                    company_info.append(f"<b>{exp['company']}</b>")
                if 'dates' in exp and exp['dates']:
                    company_info.append(exp['dates'])
                if 'location' in exp and exp['location']:
                    company_info.append(exp['location'])
                
                if company_info:
                    elements.append(Paragraph(" | ".join(company_info), styles['Company']))
                
                if 'achievements' in exp and exp['achievements']:
                    bullets = []
                    for achievement in exp['achievements']:
                        bullets.append(
                            ListItem(
                                Paragraph(achievement, styles['BulletPoint']),
                                bulletColor=colors.HexColor("#2E5D9E"),
                                value="•",
                                leftIndent=15
                            )
                        )
                    
                    elements.append(ListFlowable(bullets, bulletType='bullet', leftIndent=20))
                elements.append(Spacer(1, 8))
        
        if 'education' in resume_data and resume_data['education']:
            elements.append(Paragraph("EDUCATION", styles['SectionHeader']))
            for edu in resume_data['education']:
                edu_info = []
                if 'degree' in edu and edu['degree']:
                    edu_info.append(f"<b>{edu['degree']}</b>")
                if 'institution' in edu and edu['institution']:
                    edu_info.append(edu['institution'])
                if 'year' in edu and edu['year']:
                    edu_info.append(f"({edu['year']})")
                if 'honors' in edu and edu['honors']:
                    edu_info.append(f"<i>{edu['honors']}</i>")
                
                if edu_info:
                    elements.append(Paragraph(", ".join(edu_info), styles['BodyText']))
                    elements.append(Spacer(1, 4))
            elements.append(Spacer(1, 8))
        

        if 'skills' in resume_data and resume_data['skills']:
            elements.append(Paragraph("SKILLS", styles['SectionHeader']))
            
            if isinstance(resume_data['skills'], dict):
                for category, skills in resume_data['skills'].items():
                    if skills: 
                        elements.append(Paragraph(category.upper(), styles['SkillCategory']))
                        elements.append(Paragraph(", ".join(skills), styles['BodyText']))
                        elements.append(Spacer(1, 4))
            else:
                skill_data = []
                for i in range(0, len(resume_data['skills']), 3):
                    row = resume_data['skills'][i:i+3]
                    while len(row) < 3:
                        row.append("")
                    skill_data.append(row)
                
                if skill_data:
                    skill_table = Table(skill_data, colWidths=[doc.width/3]*3)
                    skill_table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0),
                        ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('FONTSIZE', (0,0), (-1,-1), 9),
                        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(skill_table)
            
            elements.append(Spacer(1, 12))
        

        if 'projects' in resume_data and resume_data['projects']:
            elements.append(Paragraph("PROJECTS", styles['SectionHeader']))
            for proj in resume_data['projects']:
                if 'name' in proj and proj['name']:
                    elements.append(Paragraph(f"<b>{proj['name']}</b>", styles['JobTitle']))
                if 'description' in proj and proj['description']:
                    elements.append(Paragraph(proj['description'], styles['BodyText']))
                if 'technologies' in proj and proj['technologies']:
                    elements.append(Paragraph(f"<font color='#555555'><i>Technologies: {', '.join(proj['technologies'])}</i></font>", styles['BodyText']))
                elements.append(Spacer(1, 8))

        if 'certifications' in resume_data and resume_data['certifications']:
            elements.append(Paragraph("CERTIFICATIONS", styles['SectionHeader']))
            for cert in resume_data['certifications']:
                elements.append(Paragraph(f"• {cert}", styles['BodyText']))
            elements.append(Spacer(1, 12))
    
    else:
        if 'contact_info' in st.session_state.resume_data and 'name' in st.session_state.resume_data['contact_info']:
            elements.append(Paragraph(st.session_state.resume_data['contact_info']['name'], styles['Header']))
            
            contact_parts = []
            if 'email' in st.session_state.resume_data['contact_info'] and st.session_state.resume_data['contact_info']['email']:
                contact_parts.append(st.session_state.resume_data['contact_info']['email'])
            if 'phone' in st.session_state.resume_data['contact_info'] and st.session_state.resume_data['contact_info']['phone']:
                contact_parts.append(st.session_state.resume_data['contact_info']['phone'])
            if 'location' in st.session_state.resume_data['contact_info'] and st.session_state.resume_data['contact_info']['location']:
                contact_parts.append(st.session_state.resume_data['contact_info']['location'])
            
            if contact_parts:
                elements.append(Paragraph(" | ".join(contact_parts), styles['BodyText']))
            
            elements.append(Paragraph(datetime.now().strftime("%B %d, %Y"), styles['BodyText']))
            elements.append(Spacer(1, 24))
        
        if hasattr(st.session_state, 'company_name') and st.session_state.company_name:
            elements.append(Paragraph(st.session_state.company_name, styles['BodyText']))
            elements.append(Paragraph("[Company Address]", styles['BodyText']))
            elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("Dear Hiring Manager,", styles['BodyText']))
        elements.append(Spacer(1, 12))
        
        if isinstance(resume_data, str):
            paragraphs = [p.strip() for p in resume_data.split('\n\n') if p.strip()]
            closing_added = False
            
            for para in paragraphs:
                if para.lower().startswith('sincerely'):
                    continue
                
                elements.append(Paragraph(para, styles['CoverBody']))
                elements.append(Spacer(1, 12))
            
            elements.append(Spacer(1, 24))
            elements.append(Paragraph("Sincerely,", styles['BodyText']))
            if 'contact_info' in st.session_state.resume_data and 'name' in st.session_state.resume_data['contact_info']:
                elements.append(Paragraph(st.session_state.resume_data['contact_info']['name'], styles['BodyText']))
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<font color='#888888' size=8>Generated by AI Resume Optimizer</font>", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def create_docx_cover_letter(cover_letter_text):
    """Create a DOCX document for the cover letter"""
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    for paragraph in cover_letter_text.split('\n'):
        if paragraph.strip():
            doc.add_paragraph(paragraph)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def optimize_resume_with_ai(resume_data, job_description, target_role):
    if not st.session_state.model:
        return None, "AI model not initialized. Please enter a valid Google API Key in the sidebar."
        
    prompt = f"""Transform this resume data into a professionally optimized resume for the target role. 
Rephrase all content to be more impactful and achievement-oriented while maintaining accuracy.

RESUME DATA:
{json.dumps(resume_data, indent=2)}

TARGET ROLE:
{target_role}

JOB DESCRIPTION:
{job_description}

INSTRUCTIONS:
1. Rephrase all content to be more professional and impactful
2. Focus on quantifiable achievements for work experience
3. Use industry-standard terminology
4. Maintain the original structure and information
5. Output should be valid JSON with the same structure as input
6. Do not add any new sections or information that wasn't in the original
7. Do not include the job title in the resume content

OUTPUT ONLY THE JSON:"""
    
    try:
        response = st.session_state.model.generate_content(prompt, generation_config={"temperature": 0.3})
        response_text = response.text.strip()

        if response_text.startswith("```json"):
            response_text = response_text[7:].rstrip("`").strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:].rstrip("`").strip()
        
        optimized_data = json.loads(response_text)
        
        if not isinstance(optimized_data, dict) or 'contact_info' not in optimized_data:
            return None, "Optimization failed - unexpected response format"
        
        return optimized_data, None

    except json.JSONDecodeError:
        return None, "Failed to parse the optimized resume - invalid JSON format"
    except Exception as e:
        return None, f"{str(e)}"

def generate_cover_letter_with_ai(resume_data, job_description, company_name):
    if not st.session_state.model:
        st.session_state.api_key_valid = False
        st.session_state.show_api_instructions = True
        return ""
        
    prompt = f"""Write a professional cover letter for the candidate applying to {company_name or "the company"}.

RESUME DATA:
{json.dumps(resume_data, indent=2)}

JOB DESCRIPTION:
{job_description}

INSTRUCTIONS:
1. Address to "Hiring Manager" if name is unknown
2. First paragraph should express interest in the position
3. Middle paragraphs should highlight relevant qualifications
4. Closing paragraph should express enthusiasm and request for interview
5. Keep it concise (3-4 paragraphs total)
6. Use professional but approachable tone
7. Only include one "Sincerely" closing at the end
8. Do not include any contact information in the body text

COVER LETTER:"""
    
    try:
        response = st.session_state.model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "400" in error_msg or "quota" in error_msg or "invalid" in error_msg:
            st.session_state.api_key_valid = False
            st.session_state.show_api_instructions = True
        else:
            st.error(f"Error generating cover letter: {str(e)}")
        return ""

def analyze_ats_compliance(resume_data, job_description):
    if not st.session_state.model:
        st.session_state.api_key_valid = False
        st.session_state.show_api_instructions = True
        return ""
        
    prompt = f"""Analyze this resume for ATS (Applicant Tracking System) compliance against the job description.
Provide specific recommendations to improve ATS scoring.

RESUME DATA:
{json.dumps(resume_data, indent=2)}

JOB DESCRIPTION:
{job_description}

FORMAT YOUR RESPONSE WITH THESE SECTIONS:
1. Keyword Optimization
2. Formatting Suggestions
3. Content Improvements"""
    
    try:
        response = st.session_state.model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "400" in error_msg or "quota" in error_msg or "invalid" in error_msg:
            st.session_state.api_key_valid = False
            st.session_state.show_api_instructions = True
            return ""
        else:
            return f"Error generating ATS analysis: {str(e)}"

def analyze_cover_letter_ats(cover_letter, job_description):
    if not st.session_state.model:
        st.session_state.api_key_valid = False
        st.session_state.show_api_instructions = True
        return ""
        
    prompt = f"""Analyze this cover letter for ATS (Applicant Tracking System) compliance against the job description.
Provide specific recommendations to improve ATS scoring.

COVER LETTER:
{cover_letter}

JOB DESCRIPTION:
{job_description}

FORMAT YOUR RESPONSE WITH THESE SECTIONS:
1. Keyword Optimization
2. Formatting Suggestions
3. Content Improvements"""
    
    try:
        response = st.session_state.model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "400" in error_msg or "quota" in error_msg or "invalid" in error_msg:
            st.session_state.api_key_valid = False
            st.session_state.show_api_instructions = True
            return ""
        else:
            return f"Error generating cover letter ATS analysis: {str(e)}"

def generate_interview_prep(resume_data, job_description):
    if not st.session_state.model:
        st.session_state.api_key_valid = False
        st.session_state.show_api_instructions = True
        return ""
        
    prompt = f"""Generate interview preparation materials based on this resume and job description.

RESUME DATA:
{json.dumps(resume_data, indent=2)}

JOB DESCRIPTION:
{job_description}

INCLUDE THESE SECTIONS:
1. 10 Likely Technical Questions with Sample Answers
2. 5 Behavioral Questions with Sample Answers
3. Questions to Ask the Interviewer"""
    
    try:
        response = st.session_state.model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "400" in error_msg or "quota" in error_msg or "invalid" in error_msg:
            st.session_state.api_key_valid = False
            st.session_state.show_api_instructions = True
            return ""
        else:
            return f"Error generating interview prep: {str(e)}"

def contact_info_form():
    st.subheader("Contact Information")
    cols = st.columns([1, 1])
    with cols[0]:
        st.session_state.resume_data['contact_info']['name'] = st.text_input(
            "Full Name", 
            value=st.session_state.resume_data['contact_info']['name'],
            key="name_input"
        )
        st.session_state.resume_data['contact_info']['email'] = st.text_input(
            "Email", 
            value=st.session_state.resume_data['contact_info']['email'],
            key="email_input"
        )
        st.session_state.resume_data['contact_info']['phone'] = st.text_input(
            "Phone", 
            value=st.session_state.resume_data['contact_info']['phone'],
            key="phone_input"
        )
    with cols[1]:
        st.session_state.resume_data['contact_info']['location'] = st.text_input(
            "Location", 
            value=st.session_state.resume_data['contact_info']['location'],
            key="location_input"
        )
        st.session_state.resume_data['contact_info']['linkedin'] = st.text_input(
            "LinkedIn Profile", 
            value=st.session_state.resume_data['contact_info']['linkedin'],
            key="linkedin_input"
        )

def job_info_form():
    st.subheader("Job Information")
    st.session_state.resume_data['target_role'] = st.text_input(
        "Target Job Title", 
        value=st.session_state.resume_data['target_role'],
        key="job_title_input"
    )
    st.session_state.company_name = st.text_input(
        "Company Name (optional)", 
        value=st.session_state.company_name,
        key="company_input"
    )
    st.session_state.job_description = st.text_area(
        "Job Description", 
        value=st.session_state.job_description,
        height=150,
        key="job_desc_input",
        help="Paste the job description you're applying for"
    )

def professional_summary_form():
    st.subheader("Professional Summary")
    st.session_state.resume_data['professional_summary'] = st.text_area(
        "Summary (3-5 sentences highlighting your key qualifications)", 
        value=st.session_state.resume_data['professional_summary'],
        height=100,
        key="summary_input"
    )

def work_experience_form():
    st.subheader("Work Experience")

    if 'resume_data' not in st.session_state:
        st.session_state.resume_data = {'work_experience': []}

    if 'reset_new_position_form' not in st.session_state:
        st.session_state.reset_new_position_form = False
    if st.session_state.reset_new_position_form:
        st.session_state["new_job_title_input"] = ""
        st.session_state["new_company_input"] = ""
        st.session_state["new_dates_input"] = ""
        st.session_state["new_location_input"] = ""
        st.session_state["new_achievements_input"] = ""
        st.session_state.reset_new_position_form = False 

    with st.expander("Add New Position", expanded=False):
        cols = st.columns([1, 1])
        with cols[0]:
            new_job_title = st.text_input("Job Title", key="new_job_title_input")
            new_company = st.text_input("Company", key="new_company_input")
            new_dates = st.text_input("Dates (e.g., Jan 2020 - Present)", key="new_dates_input")
        with cols[1]:
            new_location = st.text_input("Location", key="new_location_input")
            new_achievements = st.text_area(
                "Achievements (one per line)",
                height=100,
                key="new_achievements_input",
                help="Focus on quantifiable results and impact"
            )

        if st.button("Add Position", key="add_position"):
            if new_job_title or new_company:
                st.session_state.resume_data['work_experience'].append({
                    'job_title': new_job_title,
                    'company': new_company,
                    'dates': new_dates,
                    'location': new_location,
                    'achievements': [a.strip() for a in new_achievements.split('\n') if a.strip()]
                })
                st.session_state.reset_new_position_form = True
                st.rerun()
    for i, exp in enumerate(st.session_state.resume_data['work_experience']):
        with st.expander(f"{exp.get('job_title', 'Untitled')} at {exp.get('company', 'Unknown')}", expanded=False):
            cols = st.columns([1, 1])
            with cols[0]:
                updated_job_title = st.text_input(
                    "Job Title",
                    value=exp.get('job_title', ''),
                    key=f"job_title_{i}"
                )
                updated_company = st.text_input(
                    "Company",
                    value=exp.get('company', ''),
                    key=f"company_{i}"
                )
                updated_dates = st.text_input(
                    "Dates",
                    value=exp.get('dates', ''),
                    key=f"dates_{i}"
                )
            with cols[1]:
                updated_location = st.text_input(
                    "Location",
                    value=exp.get('location', ''),
                    key=f"location_{i}"
                )
                updated_achievements = st.text_area(
                    "Achievements",
                    value="\n".join(exp.get('achievements', [])),
                    height=100,
                    key=f"achievements_{i}"
                )

            cols = st.columns([1, 1])
            with cols[0]:
                if st.button("Update", key=f"update_{i}"):
                    st.session_state.resume_data['work_experience'][i] = {
                        'job_title': updated_job_title,
                        'company': updated_company,
                        'dates': updated_dates,
                        'location': updated_location,
                        'achievements': [a.strip() for a in updated_achievements.split('\n') if a.strip()]
                    }
                    st.rerun()
            with cols[1]:
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state.resume_data['work_experience'].pop(i)
                    st.rerun()


def education_form():
    st.subheader("Education")
    
    if 'resume_data' not in st.session_state:
        st.session_state.resume_data = {}
    if 'education' not in st.session_state.resume_data:
        st.session_state.resume_data['education'] = []
    if 'reset_new_education_form' not in st.session_state:
        st.session_state.reset_new_education_form = False

    if st.session_state.reset_new_education_form:
        st.session_state["new_degree"] = ""
        st.session_state["new_institution"] = ""
        st.session_state["new_year"] = ""
        st.session_state["new_honors"] = ""
        st.session_state.reset_new_education_form = False

    with st.expander("Add Education", expanded=False):
        cols = st.columns([1, 1])
        with cols[0]:
            new_degree = st.text_input("Degree", key="new_degree")
            new_institution = st.text_input("Institution", key="new_institution")
        with cols[1]:
            new_year = st.text_input("Year", key="new_year")
            new_honors = st.text_input("Honors/Awards (optional)", key="new_honors")
        
        if st.button("Add Education", key="add_education"):
            if new_degree or new_institution:
                st.session_state.resume_data['education'].append({
                    'degree': new_degree,
                    'institution': new_institution,
                    'year': new_year,
                    'honors': new_honors
                })
                st.session_state.reset_new_education_form = True
                st.rerun()

    for i, edu in enumerate(st.session_state.resume_data['education']):
        with st.expander(f"{edu.get('degree', 'Degree')} from {edu.get('institution', 'Institution')}", expanded=False):
            cols = st.columns([1, 1])
            with cols[0]:
                updated_degree = st.text_input(
                    "Degree", 
                    value=edu.get('degree', ''),
                    key=f"degree_{i}"
                )
                updated_institution = st.text_input(
                    "Institution", 
                    value=edu.get('institution', ''),
                    key=f"institution_{i}"
                )
            with cols[1]:
                updated_year = st.text_input(
                    "Year", 
                    value=edu.get('year', ''),
                    key=f"year_{i}"
                )
                updated_honors = st.text_input(
                    "Honors/Awards", 
                    value=edu.get('honors', ''),
                    key=f"honors_{i}"
                )
            
            cols = st.columns([1, 1])
            with cols[0]:
                if st.button("Update", key=f"update_edu_{i}"):
                    st.session_state.resume_data['education'][i] = {
                        'degree': updated_degree,
                        'institution': updated_institution,
                        'year': updated_year,
                        'honors': updated_honors
                    }
                    st.rerun()
            with cols[1]:
                if st.button("Remove", key=f"remove_edu_{i}"):
                    st.session_state.resume_data['education'].pop(i)
                    st.rerun()


def skills_form():
    st.subheader("Skills")
    if not isinstance(st.session_state.resume_data['skills'], dict):
        st.session_state.resume_data['skills'] = {
            'Technical': [],
            'Soft': []
        }
    
    current_tech_skills = ", ".join(st.session_state.resume_data['skills'].get('Technical', []))
    updated_tech_skills = st.text_area(
        "Technical Skills (comma separated)", 
        value=current_tech_skills,
        height=60,
        key="tech_skills_input",
        help="List your technical skills and technologies"
    )
    
    current_soft_skills = ", ".join(st.session_state.resume_data['skills'].get('Soft', []))
    updated_soft_skills = st.text_area(
        "Soft Skills (comma separated)", 
        value=current_soft_skills,
        height=60,
        key="soft_skills_input",
        help="List your soft skills and personal attributes"
    )
    
    if st.button("Save Skills", key="save_skills"):
        st.session_state.resume_data['skills'] = {
            'Technical': [s.strip() for s in updated_tech_skills.split(',') if s.strip()],
            'Soft': [s.strip() for s in updated_soft_skills.split(',') if s.strip()]
        }
        st.rerun()

def projects_form():
    st.subheader("Projects")

    if 'resume_data' not in st.session_state:
        st.session_state.resume_data = {}
    if 'projects' not in st.session_state.resume_data:
        st.session_state.resume_data['projects'] = []
    if 'reset_new_project_form' not in st.session_state:
        st.session_state.reset_new_project_form = False

    if st.session_state.reset_new_project_form:
        st.session_state["new_project_name"] = ""
        st.session_state["new_project_desc"] = ""
        st.session_state["new_project_tech"] = ""
        st.session_state.reset_new_project_form = False

    with st.expander("Add Project", expanded=False):
        new_project_name = st.text_input("Project Name", key="new_project_name")
        new_project_desc = st.text_area(
            "Description", 
            height=80,
            key="new_project_desc",
            help="Describe the project and your role"
        )
        new_project_tech = st.text_input(
            "Technologies (comma separated)", 
            key="new_project_tech",
            help="List the technologies/tools used"
        )

        if st.button("Add Project", key="add_project"):
            if new_project_name or new_project_desc:
                st.session_state.resume_data['projects'].append({
                    'name': new_project_name,
                    'description': new_project_desc,
                    'technologies': [t.strip() for t in new_project_tech.split(',') if t.strip()]
                })
                st.session_state.reset_new_project_form = True
                st.rerun()

    for i, proj in enumerate(st.session_state.resume_data['projects']):
        with st.expander(f"{proj.get('name', 'Untitled Project')}", expanded=False):
            updated_name = st.text_input(
                "Project Name", 
                value=proj.get('name', ''),
                key=f"project_name_{i}"
            )
            updated_desc = st.text_area(
                "Description", 
                value=proj.get('description', ''),
                height=80,
                key=f"project_desc_{i}"
            )
            updated_tech = st.text_input(
                "Technologies", 
                value=", ".join(proj.get('technologies', [])) if proj.get('technologies') else "",
                key=f"project_tech_{i}"
            )

            cols = st.columns([1, 1])
            with cols[0]:
                if st.button("Update", key=f"update_proj_{i}"):
                    st.session_state.resume_data['projects'][i] = {
                        'name': updated_name,
                        'description': updated_desc,
                        'technologies': [t.strip() for t in updated_tech.split(',') if t.strip()]
                    }
                    st.rerun()
            with cols[1]:
                if st.button("Remove", key=f"remove_proj_{i}"):
                    st.session_state.resume_data['projects'].pop(i)
                    st.rerun()


def certifications_form():
    st.subheader("Certifications")
    current_certs = "\n".join(st.session_state.resume_data['certifications']) if st.session_state.resume_data['certifications'] else ""
    updated_certs = st.text_area(
        "List your certifications (one per line)", 
        value=current_certs,
        height=60,
        key="certs_input",
        help="Include certification name, issuing organization, and year if applicable"
    )
    
    if st.button("Save Certifications", key="save_certs"):
        st.session_state.resume_data['certifications'] = [c.strip() for c in updated_certs.split('\n') if c.strip()]
        st.rerun()

def create_comparison_view(original, optimized):
    sections = [
        ('professional_summary', 'Professional Summary'),
        ('work_experience', 'Work Experience'),
        ('education', 'Education'),
        ('skills', 'Skills'),
        ('projects', 'Projects'),
        ('certifications', 'Certifications')
    ]
    
    st.subheader("Content Validation")
    original_sections = set(original.keys())
    optimized_sections = set(optimized.keys())
    added_sections = optimized_sections - original_sections
    
    if added_sections:
        st.warning(f"⚠️ The optimized resume added these sections that weren't in the original: {', '.join(added_sections)}")
    else:
        st.success("✅ No new sections were added to the optimized resume")
    
    if 'skills' in original and 'skills' in optimized:
        original_skills = set()
        optimized_skills = set()
        
        if isinstance(original['skills'], dict):
            for cat in original['skills']:
                original_skills.update(original['skills'][cat])
        else:
            original_skills.update(original['skills'])
        
        if isinstance(optimized['skills'], dict):
            for cat in optimized['skills']:
                optimized_skills.update(optimized['skills'][cat])
        else:
            optimized_skills.update(optimized['skills'])
        
        added_skills = optimized_skills - original_skills
        if added_skills:
            st.warning(f"⚠️ The optimized resume added these skills that weren't in the original: {', '.join(added_skills)}")
        else:
            st.success("✅ No new skills were added to the optimized resume")
    
    if 'certifications' in original and 'certifications' in optimized:
        original_certs = set(original['certifications'])
        optimized_certs = set(optimized['certifications'])
        added_certs = optimized_certs - original_certs
        
        if added_certs:
            st.warning(f"⚠️The optimized resume added these certifications that weren't in the original: {', '.join(added_certs)}")
        else:
            st.success("✅ No new certifications were added to the optimized resume")
    
    if 'projects' in original and 'projects' in optimized:
        original_projects = {p['name'].lower() for p in original['projects'] if 'name' in p}
        optimized_projects = {p['name'].lower() for p in optimized['projects'] if 'name' in p}
        added_projects = optimized_projects - original_projects
        
        if added_projects:
            st.warning(f"⚠️ The optimized resume added these projects that weren't in the original: {', '.join(added_projects)}")
        else:
            st.success("✅ No new projects were added to the optimized resume")
    
    st.markdown("---")
    
    for section_key, section_name in sections:
        if section_key in original or section_key in optimized:
            st.subheader(section_name)
            
            if section_key == 'professional_summary':
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Original**")
                    st.write(original.get(section_key, "N/A"))
                with col2:
                    st.markdown("**Optimized**")
                    st.write(optimized.get(section_key, "N/A"))
            
            elif section_key in ['work_experience', 'education']:
                max_len = max(len(original.get(section_key, [])), 
                             len(optimized.get(section_key, [])))
                
                for i in range(max_len):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Original**")
                        if i < len(original.get(section_key, [])):
                            item = original[section_key][i]
                            if section_key == 'work_experience':
                                st.write(f"**{item.get('job_title', '')}**")
                                st.write(f"{item.get('company', '')} | {item.get('dates', '')}")
                                for ach in item.get('achievements', []):
                                    st.write(f"- {ach}")
                            else: 
                                st.write(f"**{item.get('degree', '')}**")
                                st.write(f"{item.get('institution', '')} | {item.get('year', '')}")
                                if item.get('honors'):
                                    st.write(f"Honors: {item.get('honors')}")
                        else:
                            st.write("N/A")
                    
                    with col2:
                        st.markdown("**Optimized**")
                        if i < len(optimized.get(section_key, [])):
                            item = optimized[section_key][i]
                            if section_key == 'work_experience':
                                st.write(f"**{item.get('job_title', '')}**")
                                st.write(f"{item.get('company', '')} | {item.get('dates', '')}")
                                for ach in item.get('achievements', []):
                                    st.write(f"- {ach}")
                            else: 
                                st.write(f"**{item.get('degree', '')}**")
                                st.write(f"{item.get('institution', '')} | {item.get('year', '')}")
                                if item.get('honors'):
                                    st.write(f"Honors: {item.get('honors')}")
                        else:
                            st.write("N/A")
            
            elif section_key in ['skills', 'certifications']:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Original**")
                    if original.get(section_key):
                        if isinstance(original[section_key], dict):
                            for cat, skills in original[section_key].items():
                                st.write(f"**{cat}**: {', '.join(skills)}")
                        else:
                            st.write(", ".join(original[section_key]) if isinstance(original[section_key], list) 
                                    else original[section_key])
                    else:
                        st.write("N/A")
                with col2:
                    st.markdown("**Optimized**")
                    if optimized.get(section_key):
                        if isinstance(optimized[section_key], dict):
                            for cat, skills in optimized[section_key].items():
                                st.write(f"**{cat}**: {', '.join(skills)}")
                        else:
                            st.write(", ".join(optimized[section_key]) if isinstance(optimized[section_key], list) 
                                    else optimized[section_key])
                    else:
                        st.write("N/A")
            
            elif section_key == 'projects':
                max_len = max(len(original.get(section_key, [])), 
                             len(optimized.get(section_key, [])))
                
                for i in range(max_len):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Original**")
                        if i < len(original.get(section_key, [])):
                            proj = original[section_key][i]
                            st.write(f"**{proj.get('name', '')}**")
                            st.write(proj.get('description', ''))
                            if proj.get('technologies'):
                                st.write(f"Technologies: {', '.join(proj['technologies'])}")
                        else:
                            st.write("N/A")
                    
                    with col2:
                        st.markdown("**Optimized**")
                        if i < len(optimized.get(section_key, [])):
                            proj = optimized[section_key][i]
                            st.write(f"**{proj.get('name', '')}**")
                            st.write(proj.get('description', ''))
                            if proj.get('technologies'):
                                st.write(f"Technologies: {', '.join(proj['technologies'])}")
                        else:
                            st.write("N/A")
            
            st.markdown("---")

def main():
    st.set_page_config(
        page_title="𓂃🪶GenAI Resume Crafter",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown("""
    <style>
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem;
        }
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
            padding: 1.5rem;
        }
        h1 {
            margin-top: 0rem !important;
            margin-bottom: 0.5rem !important;
        }
        .stTextInput input, .stTextArea textarea {
            padding: 8px 12px !important;
        }
        .stButton>button {
            color:black;
            background-color:#FF6700;
            border-radius: 4px !important;
            padding: 8px 16px !important;
            font-weight: 500 !important;
        }
        .stButton>button:hover {
            color:black;
            background-color:#FF6700;
            border-radius: 4px !important;
            padding: 8px 16px !important;
            font-weight: 500 !important;
        }
        .stSelectbox select {
            padding: 8px 12px !important;
        }
        .resume-preview {
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .ats-improvement {
            background-color: #f0f7ff;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .highlight {
            background-color: #fffde7;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
        }
        .delete-btn {
            color: #ff4b4b !important;
            border-color: #ff4b4b !important;
        }
        .sidebar-section-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #FF6700;
            text-align: center;
        }
        .sidebar-checkbox-container {
            display: flex;
            justify-content: center;
            margin-bottom: 0.5rem;
        }
        .sidebar-checkbox {
            width: 90%;
            margin: 0 auto;
        }
        .sidebar-checkbox .stCheckbox {
            margin-left: 0.5rem;
        }
        .sidebar-checkbox label {
            display: flex;
            align-items: center;
        }
        .button-row {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .button-row button {
            flex: 1;
        }
    </style>
    """, unsafe_allow_html=True)
    st.title("𓂃🪶GenAI Resume Crafter")
    st.markdown(
        '<p style="color:#FF6700; font-size:1.3rem;">'
        'Create beautiful, professional resumes tailored to your dream job'
        '</p>',
        unsafe_allow_html=True
    )
    init_session_state()
    check_api_key()
    with st.sidebar:
        st.markdown('<div class="sidebar-section-title" style="color:#FF6700; font-size:1.5rem; padding-bottom:2px">Customize Your Resume</div>', unsafe_allow_html=True)
        with st.expander("Guide to use GenAI Resume Crafter", expanded=False):
            st.markdown("""
        **Follow these steps:**
        1. Select sections to include
        2. Fill in your resume details
        3. Enter job description
        4. Click 'Optimize Resume'
        5. Review all tabs for output
        """)
     
        st.session_state.selected_sections = []
        
        def create_checkbox(label, key, help_text):
            container = st.container()
            with container:
                cols = st.columns([1, 20])
                with cols[1]:
                    if st.checkbox(
                        label,
                        value=label in st.session_state.selected_sections,
                        key=key,
                        help=help_text
                    ):
                        st.session_state.selected_sections.append(label)
        st.markdown("Sections to Include")
        create_checkbox("Professional Summary", "summary_check", "Include a professional summary section")
        create_checkbox("Work Experience", "work_check", "Include work experience section")
        create_checkbox("Education", "edu_check", "Include education section")
        create_checkbox("Skills", "skills_check", "Include skills section")
        create_checkbox("Projects", "projects_check", "Include projects section")
        create_checkbox("Certifications", "certs_check", "Include certifications section")

        if st.session_state.show_api_instructions:
            show_api_key_input_in_sidebar()
        
        st.markdown("---")
        st.header("Actions")
        
        if st.session_state.use_default_data:
            sample_data = {
                'contact_info': {
                    'name': 'John Doe',
                    'email': 'john.doe@example.com',
                    'phone': '(555) 123-4567',
                    'location': 'San Francisco, CA',
                    'linkedin': 'linkedin.com/in/johndoe'
                },
                'target_role': 'Senior Software Engineer',
                'professional_summary': 'Experienced software engineer with 5+ years of expertise in full-stack development and cloud architecture. Strong background in designing scalable systems and leading development teams.',
                'work_experience': [
                    {
                        'job_title': 'Senior Software Engineer',
                        'company': 'Tech Innovations Inc',
                        'dates': '2020 - Present',
                        'location': 'San Francisco, CA',
                        'achievements': [
                            'Led migration to microservices architecture, reducing system latency by 40%',
                            'Implemented CI/CD pipeline that decreased deployment time by 65%'
                        ]
                    }
                ],
                'education': [
                    {
                        'degree': 'Master of Science in Computer Science',
                        'institution': 'Stanford University',
                        'year': '2018'
                    }
                ],
                'skills': {
                    'Technical': ['Python', 'JavaScript', 'React', 'Node.js', 'AWS'],
                    'Soft': ['Team Leadership', 'Communication']
                },
                'projects': [
                    {
                        'name': 'E-commerce Platform',
                        'description': 'Developed a full-stack e-commerce solution with payment integration',
                        'technologies': ['React', 'Node.js', 'MongoDB']
                    }
                ],
                'certifications': [
                    'AWS Certified Solutions Architect - Associate'
                ]
            }
            
            for key in sample_data:
                if not st.session_state.resume_data.get(key) or (
                    isinstance(st.session_state.resume_data.get(key), (dict, list)) and 
                    not st.session_state.resume_data.get(key)
                ):
                    st.session_state.resume_data[key] = sample_data[key]
            
            if not st.session_state.job_description:
                st.session_state.job_description = """We are seeking a Senior Software Engineer to join our growing team. The ideal candidate will have:
- 5+ years of software development experience
- Expertise in Python and JavaScript
- Experience with cloud platforms (AWS preferred)
- Strong understanding of microservices architecture
- Leadership experience mentoring junior engineers"""
            
            if not st.session_state.company_name:
                st.session_state.company_name = "Innovative Tech Solutions"

        cols = st.columns(2)
        with cols[0]:
            if st.button("Optimize Resume", use_container_width=True, type="primary"):
                if not st.session_state.resume_data['contact_info']['name']:
                    st.error("Please enter your name")
                elif not st.session_state.resume_data['target_role']:
                    st.error("Please enter target job title")
                elif not st.session_state.job_description:
                    st.error("Please enter job description")
                elif not st.session_state.api_key_valid:
                    if st.session_state.user_api_key:
                        valid, message = configure_api(st.session_state.user_api_key)
                        if valid:
                            st.session_state.api_key_valid = True
                            st.session_state.show_api_instructions = False
                        else:
                            st.error("Invalid API key. Please check your key and try again.")
                            st.session_state.show_api_instructions = True
                            st.rerun()
                            return
                    else:
                        st.error("Please enter a valid Google API Key in the sidebar to use AI features")
                        st.session_state.show_api_instructions = True
                        st.rerun()
                        return
                else:
                    filtered_resume = {
                        'contact_info': st.session_state.resume_data['contact_info'],
                        'target_role': st.session_state.resume_data['target_role']
                    }
                    
                    if "Professional Summary" in st.session_state.selected_sections:
                        filtered_resume['professional_summary'] = st.session_state.resume_data.get('professional_summary', '')
                    
                    if "Work Experience" in st.session_state.selected_sections:
                        filtered_resume['work_experience'] = st.session_state.resume_data.get('work_experience', [])
                    
                    if "Education" in st.session_state.selected_sections:
                        filtered_resume['education'] = st.session_state.resume_data.get('education', [])
                    
                    if "Skills" in st.session_state.selected_sections:
                        filtered_resume['skills'] = st.session_state.resume_data.get('skills', {})
                    
                    if "Projects" in st.session_state.selected_sections:
                        filtered_resume['projects'] = st.session_state.resume_data.get('projects', [])
                    
                    if "Certifications" in st.session_state.selected_sections:
                        filtered_resume['certifications'] = st.session_state.resume_data.get('certifications', [])
                    
                    optimized_resume, error = optimize_resume_with_ai(
                        filtered_resume,
                        st.session_state.job_description,
                        st.session_state.resume_data['target_role']
                    )

                    if optimized_resume is None:
                        if "API key" in error or "model not initialized" in error or "400" in error or "API_KEY" in error:
                            st.session_state.api_key_valid = False
                            st.session_state.show_api_instructions = True
                            st.rerun()
                        else:
                            st.error(f"Error optimizing resume: {error}")
                    else:
                        st.session_state.optimized_resume = optimized_resume
                        st.session_state.cover_letter = generate_cover_letter_with_ai(
                            st.session_state.optimized_resume,
                            st.session_state.job_description,
                            st.session_state.company_name
                        )
                        st.session_state.cover_letter_ats = analyze_cover_letter_ats(
                            st.session_state.cover_letter,
                            st.session_state.job_description
                        )
                        st.session_state.ats_report = analyze_ats_compliance(
                            st.session_state.optimized_resume,
                            st.session_state.job_description
                        )
                        st.session_state.interview_prep = generate_interview_prep(
                            st.session_state.optimized_resume,
                            st.session_state.job_description
                        )
                        st.session_state.show_comparison = True
                        st.success("✅ Resume optimization completed!")
                        st.rerun()

        with cols[1]:
            if st.button("Reset Form", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                init_session_state()
                st.rerun()

        if st.session_state.optimized_resume:
            st.markdown("---")
            st.subheader("Download")
            pdf_buffer = create_pdf_document(st.session_state.optimized_resume, is_resume=True)
            st.download_button(
                label="📥 Download Resume (PDF)",
                data=pdf_buffer,
                file_name=f"optimized_resume_{st.session_state.optimized_resume['contact_info']['name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    if st.session_state.auto_optimize and st.session_state.api_key_valid:
        st.session_state.auto_optimize = False
        
        if (st.session_state.resume_data['contact_info']['name'] and 
            st.session_state.resume_data['target_role'] and 
            st.session_state.job_description):
            
            filtered_resume = {
                'contact_info': st.session_state.resume_data['contact_info'],
                'target_role': st.session_state.resume_data['target_role']
            }
            
            if "Professional Summary" in st.session_state.selected_sections:
                filtered_resume['professional_summary'] = st.session_state.resume_data.get('professional_summary', '')
            
            if "Work Experience" in st.session_state.selected_sections:
                filtered_resume['work_experience'] = st.session_state.resume_data.get('work_experience', [])
            
            if "Education" in st.session_state.selected_sections:
                filtered_resume['education'] = st.session_state.resume_data.get('education', [])
            
            if "Skills" in st.session_state.selected_sections:
                filtered_resume['skills'] = st.session_state.resume_data.get('skills', {})
            
            if "Projects" in st.session_state.selected_sections:
                filtered_resume['projects'] = st.session_state.resume_data.get('projects', [])
            
            if "Certifications" in st.session_state.selected_sections:
                filtered_resume['certifications'] = st.session_state.resume_data.get('certifications', [])
            
            optimized_resume, error = optimize_resume_with_ai(
                filtered_resume,
                st.session_state.job_description,
                st.session_state.resume_data['target_role']
            )

            if optimized_resume is None:
                if "API key" in error or "model not initialized" in error or "400" in error or "API_KEY" in error:
                    st.session_state.api_key_valid = False
                    st.session_state.show_api_instructions = True
                    st.rerun()
                else:
                    st.error(f"Error optimizing resume: {error}")
            else:
                st.session_state.optimized_resume = optimized_resume
                st.session_state.cover_letter = generate_cover_letter_with_ai(
                    st.session_state.optimized_resume,
                    st.session_state.job_description,
                    st.session_state.company_name
                )
                st.session_state.cover_letter_ats = analyze_cover_letter_ats(
                    st.session_state.cover_letter,
                    st.session_state.job_description
                )
                st.session_state.ats_report = analyze_ats_compliance(
                    st.session_state.optimized_resume,
                    st.session_state.job_description
                )
                st.session_state.interview_prep = generate_interview_prep(
                    st.session_state.optimized_resume,
                    st.session_state.job_description
                )
                st.session_state.show_comparison = True
                st.success("✅ Resume optimization completed!")
                st.rerun()
        else:
            st.warning("Please fill in your name, target role, and job description")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Resume Builder", 
        "Optimized Resume", 
        "Cover Letter", 
        "Comparison", 
        "ATS Analysis", 
        "Interview Preparation"
    ])

    with tab1:
        contact_info_form()
        job_info_form()
        
        if "Professional Summary" in st.session_state.selected_sections:
            professional_summary_form()
        if "Work Experience" in st.session_state.selected_sections:
            work_experience_form()
        if "Education" in st.session_state.selected_sections:
            education_form()
        if "Skills" in st.session_state.selected_sections:
            skills_form()
        if "Projects" in st.session_state.selected_sections:
            projects_form()
        if "Certifications" in st.session_state.selected_sections:
            certifications_form()
    
    with tab2:
        if st.session_state.optimized_resume is None:
            st.info("Optimize the resume to see tailored results here")
        elif st.session_state.optimized_resume:
            st.subheader("Optimized Resume")
            with st.expander("View Optimized Resume Data", expanded=True):
                st.json(st.session_state.optimized_resume)

                pdf_buffer = create_pdf_document(st.session_state.optimized_resume, is_resume=True)
                st.download_button(
                    label="Download Optimized Resume (PDF)",
                    data=pdf_buffer,
                    file_name=f"optimized_resume_{st.session_state.optimized_resume['contact_info']['name'].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("Optimize your resume to see tailored results here")

    with tab3:
        if st.session_state.cover_letter:
            st.subheader("Generated Cover Letter")
            col1, col2 = st.columns(2)
        
            with col1:
                st.markdown("""
            <style>
                .scroll-container {
                    height: 400px;
                    overflow-y: auto;
                    border: 1px solid #e0e0e0;
                    padding: 15px;
                    white-space: pre-wrap;
                    font-family: "Times New Roman", Times, serif;
                    font-size: 12pt;
                    line-height: 1.5;
                    background-color: #0B0F19;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 10px;
                }
                .section-title {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
            </style>
            <div class="section-title">Cover Letter Preview</div>
            """, unsafe_allow_html=True)
            
                st.markdown(f'<div class="scroll-container">{st.session_state.cover_letter}</div>', 
                      unsafe_allow_html=True)
            
                cover_docx_buffer = create_docx_cover_letter(st.session_state.cover_letter)
                st.download_button(
                label="📄 Download Cover Letter",
                data=cover_docx_buffer,
                file_name=f"cover_letter_{st.session_state.company_name or 'application'}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

            with col2:
                  st.markdown("""
    <style>
        .scroll-container-ats {
            height: 400px;
            overflow-y: auto;

            padding: 15px;

            font-family: Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.5;
            background-color: #0B0F19;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 10px;
        }
        .section-title {
            font-weight: bold;
            margin-bottom: 5px;
        }
    </style>
    <div class="section-title">ATS Compliance Analysis</div>
    """, unsafe_allow_html=True)

                  st.markdown(
        f'<div class="scroll-container-ats">{st.session_state.cover_letter_ats}</div>',
        unsafe_allow_html=True
    )
            
        else:
            st.info("Optimize your resume to generate a cover letter")

    with tab4:
        if st.session_state.show_comparison and st.session_state.optimized_resume:
            st.header("Resume Comparison")
            st.markdown("Compare your original resume with the AI-optimized version")
            
            filtered_original = {
                'contact_info': st.session_state.resume_data['contact_info'],
                'target_role': st.session_state.resume_data['target_role']
            }
            
            if "Professional Summary" in st.session_state.selected_sections:
                filtered_original['professional_summary'] = st.session_state.resume_data.get('professional_summary', '')
            
            if "Work Experience" in st.session_state.selected_sections:
                filtered_original['work_experience'] = st.session_state.resume_data.get('work_experience', [])
            
            if "Education" in st.session_state.selected_sections:
                filtered_original['education'] = st.session_state.resume_data.get('education', [])
            
            if "Skills" in st.session_state.selected_sections:
                filtered_original['skills'] = st.session_state.resume_data.get('skills', {})
            
            if "Projects" in st.session_state.selected_sections:
                filtered_original['projects'] = st.session_state.resume_data.get('projects', [])
            if "Certifications" in st.session_state.selected_sections:
                filtered_original['certifications'] = st.session_state.resume_data.get('certifications', [])
            create_comparison_view(filtered_original, st.session_state.optimized_resume)
        else:
            st.info("Optimize your resume first to see the comparison")
    with tab5:
        if st.session_state.optimized_resume and st.session_state.ats_report:
            st.subheader("ATS Compliance Report")
            st.markdown(st.session_state.ats_report)
        elif st.session_state.optimized_resume:
            st.subheader("ATS Compliance Report")
            with st.spinner("Generating ATS analysis..."):
                st.session_state.ats_report = analyze_ats_compliance(
                    st.session_state.optimized_resume,
                    st.session_state.job_description
                )
            st.markdown(st.session_state.ats_report)
        else:
            st.info("Optimize your resume to view ATS analysis")
    with tab6:
        if st.session_state.optimized_resume and st.session_state.interview_prep:
            st.subheader("Interview Preparation Questions")
            st.markdown(st.session_state.interview_prep)
        elif st.session_state.optimized_resume:
            st.subheader("Interview Preparation Questions")
            with st.spinner("Generating interview questions..."):
                st.session_state.interview_prep = generate_interview_prep(
                    st.session_state.optimized_resume,
                    st.session_state.job_description
                )
            st.markdown(st.session_state.interview_prep)
        else:
            st.info("Optimize your resume to get interview preparation tips")
if __name__ == "__main__":
    main()