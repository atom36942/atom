# import
import asyncio
import asyncpg
import random
from datetime import date, datetime, timedelta, timezone
from config import config_postgres_url
# logic
async def execute():
    db_url = config_postgres_url
    if not db_url:
        print("Error: 'config_postgres_url' is not set in environment or config.")
        return
    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    random.seed(20260602)
    now = datetime.now(timezone.utc)
    job_count = 1000
    candidates_per_job = 5
    jobs = [
        ("Senior Backend Engineer", "Own Python APIs, PostgreSQL performance, async workers, and service reliability for a hiring platform.", "United States", 1, 3, 1, True, 145000, 175000, 6.0, 9.0, "USD", ["Python", "FastAPI", "PostgreSQL", "Redis", "AWS"], "Remote - United States", 5),
        ("Frontend Engineer", "Build polished recruiter dashboards, candidate review workflows, reusable UI components, and accessible product surfaces.", "United States", 1, 2, 1, True, 125000, 155000, 4.0, 7.0, "USD", ["React", "TypeScript", "Next.js", "Tailwind", "Playwright"], "Remote - United States", 5),
        ("Engineering Manager", "Lead a product engineering squad, coach senior engineers, improve delivery cadence, and partner closely with product.", "United States", 15, 1, 1, False, 165000, 210000, 8.0, 12.0, "USD", ["People Management", "System Design", "Agile", "Hiring", "Architecture"], "New York", 5),
        ("Product Designer", "Design recruiter workflows, candidate review screens, prototypes, and accessible design-system components.", "India", 16, 2, 1, False, 2800000, 3800000, 4.0, 7.0, "INR", ["Figma", "Design Systems", "Research", "Prototyping"], "Bengaluru", 5),
        ("UX Researcher", "Plan studies, interview recruiters and candidates, synthesize product insights, and help teams make evidence-led decisions.", "India", 16, 1, 1, True, 2200000, 3200000, 4.0, 7.0, "INR", ["User Interviews", "Survey Design", "Research Ops", "Journey Mapping"], "Remote - India", 5),
        ("Data Analyst", "Build hiring funnel dashboards, define metrics, and convert candidate signals into useful operating insight.", "India", 14, 2, 1, False, 1800000, 2600000, 3.0, 5.5, "INR", ["SQL", "Python", "Tableau", "dbt", "Statistics"], "Hyderabad", 5),
        ("Machine Learning Engineer", "Improve candidate matching, ranking signals, model evaluation, and production ML pipelines for hiring data.", "India", 11, 2, 1, True, 3000000, 4600000, 4.5, 8.0, "INR", ["Python", "PyTorch", "Feature Engineering", "MLOps", "PostgreSQL"], "Remote - India", 5),
        ("QA Automation Engineer", "Expand API and browser automation coverage, own regression quality, and improve release confidence.", "India", 13, 2, 1, True, 1600000, 2400000, 3.5, 6.0, "INR", ["Playwright", "Pytest", "API Testing", "CI/CD"], "Remote - India", 5),
        ("DevOps Engineer", "Improve deployments, observability, incident response, infrastructure automation, and production reliability.", "India", 7, 2, 3, True, 2400000, 3600000, 5.0, 8.5, "INR", ["AWS", "Kubernetes", "Terraform", "Docker", "Prometheus"], "Remote - India", 5),
        ("People Operations Manager", "Lead onboarding, HR operations, policy workflows, employee lifecycle programs, and manager support.", "United States", 2, 1, 1, False, 95000, 125000, 6.0, 10.0, "USD", ["HRIS", "Onboarding", "Employee Relations", "Compliance"], "Austin", 5),
        ("Product Manager", "Shape product discovery, define roadmap priorities, align stakeholders, and ship recruiter productivity features.", "United States", 10, 1, 1, True, 135000, 170000, 5.0, 8.5, "USD", ["Roadmapping", "Discovery", "Analytics", "B2B SaaS", "Agile"], "Remote - United States", 5),
        ("Account Executive", "Manage mid-market pipeline, run discovery, build business cases, and close new SaaS revenue.", "United Kingdom", 3, 2, 1, False, 68000, 92000, 4.0, 7.0, "GBP", ["Salesforce", "Discovery", "Negotiation", "SaaS Sales"], "London", 5),
        ("Customer Success Lead", "Guide enterprise rollout, build adoption plans, manage renewals, and surface customer feedback to product.", "United Kingdom", 9, 1, 1, False, 72000, 94000, 5.0, 8.0, "GBP", ["Customer Success", "SaaS", "Renewals", "CRM"], "London", 5),
        ("Finance Analyst", "Own monthly reporting, hiring budget tracking, variance analysis, and workforce planning models.", "United Kingdom", 5, 1, 1, False, 56000, 74000, 3.0, 5.0, "GBP", ["Excel", "FP&A", "Forecasting", "SQL", "Reporting"], "Manchester", 5),
    ]
    candidates = [
        ("Priya", "Nair", 2, "Kochi", "NIT Calicut", "Freshworks", "Zoho"),
        ("Jordan", "Ellis", 4, "Seattle", "University of Washington", "Stripe", "Tableau"),
        ("Aarav", "Mehta", 1, "Bengaluru", "IIT Bombay", "Razorpay", "Paytm"),
        ("Maya", "Thompson", 2, "Austin", "University of Texas", "Indeed", "Dell"),
        ("Nikhil", "Rao", 1, "Hyderabad", "IIIT Hyderabad", "Microsoft", "Swiggy"),
        ("Emily", "Carter", 2, "London", "University of Manchester", "HubSpot", "Zendesk"),
        ("Kabir", "Singh", 1, "Pune", "College of Engineering Pune", "Atlassian", "Infosys"),
        ("Lena", "Brooks", 2, "New York", "NYU", "Asana", "Squarespace"),
        ("Ananya", "Menon", 2, "Chennai", "Anna University", "Chargebee", "Cognizant"),
        ("Marcus", "Reed", 1, "Chicago", "Northwestern University", "Shopify", "Salesforce"),
        ("Sara", "Ahmed", 2, "Dubai", "BITS Pilani Dubai", "Careem", "Talabat"),
        ("Vikram", "Iyer", 1, "Noida", "Delhi Technological University", "Adobe", "HCLTech"),
        ("Isha", "Gupta", 2, "Mumbai", "University of Mumbai", "BrowserStack", "TCS"),
        ("Noah", "Williams", 1, "San Francisco", "UC Berkeley", "Airbnb", "Twilio"),
        ("Sofia", "Martinez", 2, "Denver", "University of Colorado", "Gusto", "SendGrid"),
        ("Rohan", "Kapoor", 1, "Delhi", "BITS Pilani", "Setu", "Ola"),
        ("Fatima", "Khan", 2, "Bengaluru", "Christ University", "PhonePe", "Infosys"),
        ("Daniel", "Wright", 1, "Manchester", "University of Leeds", "Sage", "Barclays"),
        ("Meera", "Sharma", 2, "Gurugram", "IIM Lucknow", "Zomato", "MakeMyTrip"),
        ("Chris", "Morgan", 4, "Bristol", "University of Bristol", "Monzo", "Wise"),
        ("Tanvi", "Shah", 2, "Ahmedabad", "Nirma University", "CRED", "Wipro"),
        ("Oliver", "Hughes", 1, "London", "King's College London", "Intercom", "Zendesk"),
        ("Ravi", "Narayanan", 1, "Coimbatore", "PSG College of Technology", "Freshworks", "Zoho"),
        ("Leah", "Green", 2, "Boston", "Boston University", "HubSpot", "Wayfair"),
    ]
    sources = ["LinkedIn", "Employee Referral", "Inbound Application", "Naukri", "Indeed", "Agency Partner", "Campus Alumni", "Meetup"]
    panels = [["Meera Sharma", "Alex Kim"], ["Daniel Wright", "Neha Bansal"], ["Fatima Khan", "Chris Morgan"], ["Ravi Narayanan", "Leah Green"], ["Irene Roberts", "Kabir Malhotra"]]
    qualifications = ["B.Tech Computer Science", "M.S. Information Systems", "MBA", "B.Des Interaction Design", "B.Sc Statistics", "M.Tech Software Engineering", "B.Com Finance", "M.A. Human Resources"]
    remarks = ["Recruiter screen completed; candidate is aligned on role scope and compensation.", "Hiring team liked the resume; deeper round needed to validate project ownership.", "Strong communication and domain exposure; notice period needs confirmation.", "Good practical experience, but compensation expectations need manager review.", "Candidate is available soon and has worked on similar scale problems."]
    city_map = {"INR": ["Kochi", "Bengaluru", "Hyderabad", "Pune", "Chennai", "Noida", "Mumbai", "Delhi", "Gurugram", "Ahmedabad", "Coimbatore"], "USD": ["Seattle", "Austin", "New York", "San Francisco", "Denver", "Chicago", "Boston"], "GBP": ["London", "Manchester", "Bristol"]}
    counts = {"job": 0, "candidate": 0, "interview": 0, "action_candidate_feedback": 0}
    try:
        async with conn.transaction():
            seq = 0
            for job_index in range(1, job_count + 1):
                base_job = jobs[(job_index - 1) % len(jobs)]
                salary_shift = random.randint(-5, 8) * max(1000, base_job[7] // 100)
                focus = random.choice(["Growth", "Platform", "Enterprise", "Core Product", "International", "Automation", "Analytics"])
                salary_min = max(1, base_job[7] + salary_shift)
                salary_max = max(salary_min + max(5000, base_job[8] // 20), base_job[8] + salary_shift)
                job = (f"{base_job[0]} - {focus} Req {job_index:04d}", f"{base_job[1]} Team focus: {focus.lower()} roadmap and measurable hiring outcomes.", base_job[2], base_job[3], random.randint(1, max(2, base_job[4] + 2)), base_job[5], base_job[6], salary_min, salary_max, base_job[9], base_job[10], base_job[11], base_job[12] + random.sample(["Stakeholder Management", "Documentation", "Mentoring", "Data Quality", "Security", "Experimentation"], 2), base_job[13], random.choice([2, 3, 5, 5, 5, 6]))
                job_id = await conn.fetchval(
                    "INSERT INTO job (created_by_id, updated_by_id, verified_at, verified_by_id, profile, description, country, department, quantity, employment_type, is_remote, salary_min, salary_max, experience_min, experience_max, currency, skills, closing_date, location, status) VALUES (1, 1, $1, 1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17) RETURNING id",
                    now - timedelta(days=random.randint(1, 10)), job[0], job[1], job[2], job[3], job[4], job[5], job[6], job[7], job[8], job[9], job[10], job[11], job[12], date.today() + timedelta(days=random.randint(25, 45)), job[13], job[14]
                )
                counts["job"] += 1
                if job_index % 100 == 0:
                    print(f" - Seeded {job_index}/{job_count} jobs... latest job_id={job_id}")
                for _ in range(candidates_per_job):
                    seq += 1
                    candidate_pool = [item for item in candidates if item[3] in city_map[job[11]]]
                    first, last, gender, city, college, current_company, past_company = candidate_pool[(seq + job_index) % len(candidate_pool)]
                    name = f"{first} {chr(65 + seq % 26)}. {last}"
                    slug = name.lower().replace(".", "").replace(" ", "-")
                    rating = round(random.triangular(2.8, 5.0, 4.0), 1)
                    status = random.choice([2, 2, 3, 3, 4, 5, 11, 13, 14, 15])
                    rating = min(rating, round(random.uniform(2.5, 3.4), 1)) if status == 11 else max(rating, round(random.uniform(4.0, 4.8), 1)) if status in (5, 14, 15) else rating
                    candidate_skills = random.sample(job[12], min(len(job[12]), random.randint(4, 6)))
                    experience = round(max(0.5, job[9] + random.uniform(-0.8, 1.8)), 1)
                    ctc_current = max(1, job[7] - random.randint(0, max(1, job[8] - job[7]) // 5))
                    ctc_expected = min(job[8], ctc_current + random.randint(max(1, job[8] - job[7]) // 8, max(2, job[8] - job[7]) // 3))
                    notice_period = 0 if status in (5, 15) and random.random() < 0.35 else random.choice([15, 30, 45, 60, 75, 90])
                    mobile = f"+91-90000-{seq:05d}" if job[11] == "INR" else f"+44-7700-{seq:05d}" if job[11] == "GBP" else f"+1-555-01{seq:04d}"
                    candidate_id = await conn.fetchval(
                        "INSERT INTO candidate (created_by_id, updated_by_id, verified_at, verified_by_id, job_id, profile, name, email, mobile, college, resume_url, video_url, skills, experience, company_current, company_past, ctc_current, ctc_expected, currency, notice_period_days, location_current, location_preferred, qualification_highest, source, linkedin_url, github_url, portfolio_url, languages, gender, date_of_birth, worker_status, worker_retry_count, worker_next_retry_at, worker_processed_at, worker_last_error, ai_remark, ai_rating, remark, rating, status) VALUES (1, 1, $1, 1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, 3, 0, $28, $29, NULL, $30, $31, $32, $33, $34) RETURNING id",
                        now - timedelta(days=random.randint(1, 30)), job_id, job[0], name, f"{slug}.{job_id}.{seq}@candidate.example.com", mobile, college, f"https://cdn.example.com/resumes/{slug}-{job_id}.pdf", f"https://cdn.example.com/video-intros/{slug}-{job_id}.mp4" if seq % 4 == 0 else None, candidate_skills, experience, current_company, past_company, ctc_current, ctc_expected, job[11], notice_period, city, [job[13], city] if city not in job[13] else [job[13]], qualifications[seq % len(qualifications)], sources[seq % len(sources)], f"https://linkedin.example.com/in/{slug}-{seq}", f"https://github.example.com/{slug}-{seq}" if job[3] in (1, 7, 11, 13, 14) else None, f"https://portfolio.example.com/{slug}-{seq}" if job[3] in (10, 16) else None, ["English", "Hindi"] if job[11] == "INR" else ["English", random.choice(["Spanish", "French", "German"])], gender, date(1978 + seq % 22, 1 + seq % 11, 5 + seq % 20), now, now - timedelta(hours=random.randint(1, 120)), f"Matches {job[0]} with {experience} years of experience and strengths in {', '.join(candidate_skills[:3])}.", rating, remarks[seq % len(remarks)], rating, status
                    )
                    counts["candidate"] += 1
                    interview_count = 1 if status in (2, 11, 13) else 2 if status in (3, 4) else 3
                    last_interview_id = None
                    for i in range(interview_count):
                        interview_status = 4 if status in (4, 5, 11, 14, 15) or i < interview_count - 1 else random.choice([1, 2, 5])
                        scheduled_at = now - timedelta(days=random.randint(1, 18), hours=random.randint(0, 8)) if interview_status == 4 else now + timedelta(days=random.randint(1, 14), hours=random.randint(0, 8))
                        last_interview_id = await conn.fetchval(
                            "INSERT INTO interview (created_by_id, updated_by_id, verified_at, verified_by_id, candidate_id, type, title, description, meeting_url, location, scheduled_at, duration_minutes, panel, status) VALUES (1, 1, $1, 1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) RETURNING id",
                            now - timedelta(days=1), candidate_id, [1, 2, 3][i], f"{job[0]} - {['Recruiter Screen', 'Technical / Portfolio Round', 'Hiring Manager Round'][i]}", f"{name} interview for {job[0]} covering role fit, {candidate_skills[0]}, and compensation expectations.", f"https://meet.example.com/job-{job_id}/candidate-{candidate_id}/round-{i + 1}", "Video Call" if job[6] else job[13], scheduled_at, [30, 60, 45][i], panels[(seq + i) % len(panels)], interview_status
                        )
                        counts["interview"] += 1
                    await conn.execute(
                        "INSERT INTO action_candidate_feedback (created_by_id, updated_by_id, candidate_id, description, rating, job_id, interview_id) VALUES (1, 1, $1, $2, $3, $4, $5)",
                        candidate_id, f"{name} is {'recommended for next step' if rating >= 4 else 'kept under review' if rating >= 3.3 else 'not recommended for this opening'}. Strengths: {', '.join(candidate_skills[:3])}. Notice period: {notice_period} days.", rating, job_id, last_interview_id
                    )
                    counts["action_candidate_feedback"] += 1
        print("\nJob flow data seeded successfully!")
        for table, count in counts.items():
            print(f" - {table}: {count}")
    except Exception as e:
        print(f"Error while inserting job flow data: {e}")
    finally:
        await conn.close()
# init
if __name__ == "__main__":
    asyncio.run(execute())
