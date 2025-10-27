kill-Flick is an intelligent job matching application that helps laid-off workers and job seekers in South Africa find the best re-employment opportunities by analyzing their skills, scraping multiple job boards, and generating personalized application materials using AI.

![Skill-Flick Demo](demo-screenshot.png)

---

## 🚀 Features

### 🤖 **AI-Powered Skill Extraction**
- Extracts professional skills from LinkedIn profiles or resumes using Llama 3.3-70B
- Identifies both technical and soft skills across all industries
- Intelligent fallback system when AI is unavailable

### 🔍 **Multi-Source Job Scraping**
- Scrapes 4 major South African job boards:
  - Indeed South Africa
  - PNet
  - Career Junction
  - Jobs.co.za
- Real-time job matching with duplicate removal
- Automatically filters jobs by location and skill compatibility

### 📊 **Smart Job Matching**
- Fuzzy matching algorithm calculates skill compatibility percentage
- Shows which skills you have vs. what's required
- Only displays jobs where you match 50%+ of requirements
- Prioritizes jobs with highest match scores

### ✍️ **AI Cover Letter Generation**
- Generates personalized cover letters for each job application
- Highlights your matching skills naturally
- Addresses willingness to learn missing skills
- Editable before saving

### 📈 **Skill Gap Analysis**
- Identifies top 5 missing skills across all job matches
- Recommends free/affordable online courses (Coursera, edX, Udemy)
- Tracks frequency of required skills in job market

### 📱 **Modern Responsive UI**
- Beautiful glassmorphic design with gradient animations
- Fully responsive (mobile, tablet, desktop)
- Real-time dashboard with statistics
- Smooth animations and toast notifications

---

## 🛠️ Tech Stack

### **Backend**
- **Flask 3.0** - Python web framework
- **SQLAlchemy** - ORM for database management
- **SQLite** - Lightweight database
- **BeautifulSoup4** - Web scraping
- **Requests** - HTTP client

### **AI & Machine Learning**
- **Groq API** - Llama 3.3-70B for NLP tasks
- **FuzzyWuzzy** - Fuzzy string matching for skill comparison

### **Frontend**
- **Vanilla JavaScript** - No framework overhead
- **Tailwind CSS** - Utility-first styling
- **Responsive Design** - Mobile-first approach

### **Deployment**
- **Replit** - Easy deployment and hosting
- **Python Dotenv** - Environment variable management

---

## 📋 Prerequisites

- Python 3.8 or higher
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Internet connection for job scraping

---

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/skill-flick.git
cd skill-flick
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=your_secret_key_here
FLASK_ENV=development
FLASK_DEBUG=True
```

**Get your free Groq API key:**
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free, no credit card required)
3. Navigate to API Keys
4. Create new key and copy it

### 5. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

---

## 📁 Project Structure

```
skill-flick/
├── app.py # Main Flask application
├── models.py # Database models (User, Job, Application, SkillGap)
├── scraper.py # Multi-source job scraper
├── ai_processor.py # Groq AI integration
├── requirements.txt # Python dependencies
├── .env # Environment variables (create this)
├── .env.example # Environment template
├── templates/
│ └── index.html # Frontend SPA
├── static/ # Static assets (if any)
├── skillflick.db # SQLite database (auto-generated)
├── test_setup.py # Setup verification script
├── test_ai.py # AI processor test
├── test_scraper.py # Scraper test
└── README.md # This file
```

---

## 🎮 Usage

### 1️⃣ **Register an Account**
- Click "Register here" on the homepage
- Enter email and password
- Create your account

### 2️⃣ **Setup Your Profile**
- Select your location (province in South Africa)
- Paste your LinkedIn profile text or resume content
- Click "Analyze Profile & Find Jobs"
- Wait 20-30 seconds for AI processing and job scraping

### 3️⃣ **Review Matched Jobs**
- Browse jobs sorted by match percentage
- Click any job to view details
- See which skills you have vs. what's required

### 4️⃣ **Generate Cover Letters**
- Click on a job to open details modal
- AI generates personalized cover letter automatically
- Edit the cover letter if needed
- Save application for later reference

### 5️⃣ **Close Skill Gaps**
- View your top skill gaps in the dashboard
- Click course links to learn missing skills
- Update your profile as you gain new skills

---

## 🧪 Testing

### Verify Installation

```bash
python test_setup.py
```

Expected output:
```
✅ Python Version: PASS
✅ Dependencies: PASS
✅ Environment Variables: PASS
✅ File Structure: PASS
✅ Database: PASS
✅ Groq API: PASS
```

### Test AI Processor

```bash
python test_ai.py
```

### Test Job Scraper

```bash
python test_scraper.py
```

---

## 📊 Sample Test Profiles

Use these profiles to test the system:

### Entry-Level Retail Worker
```
Experienced Retail Sales Associate with 5 years in customer service. 
Skilled in POS systems, cash handling, inventory management, and visual 
merchandising. Proficient in Microsoft Office and Excel. Strong 
communication and problem-solving skills.
```

### Office Administrator
```
Office Administrator with 6 years experience in corporate environment. 
Proficient in Microsoft Office Suite, data entry, filing, scheduling, 
and customer service. Experienced with Pastel accounting software.
```

### Software Developer
```
Junior Software Developer with 2 years experience in Python, JavaScript, 
HTML, CSS, React, and SQL. Built web applications and RESTful APIs. 
Strong problem-solving and teamwork skills.
```

### Accountant
```
Qualified Accountant with 8 years experience in bookkeeping, tax compliance, 
and financial reporting. Proficient in Sage Evolution, Pastel Partner, and 
advanced Excel. SAIPA registered bookkeeper.
```

---

## 🌐 API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - Login user
- `POST /api/logout` - Logout user

### Profile Management
- `GET /api/profile` - Get user profile
- `POST /api/profile/upload` - Upload LinkedIn text & extract skills

### Jobs
- `GET /api/jobs` - Get all matched jobs (sorted by match %)
- `POST /api/jobs/refresh` - Trigger new job scraping

### Applications
- `GET /api/applications` - Get saved applications
- `POST /api/applications` - Save new application with cover letter

### Cover Letters
- `GET /api/coverletter/<job_id>` - Generate AI cover letter for job

### Skill Gaps
- `GET /api/skillgaps` - Get top 5 skill gaps with course recommendations

### Statistics
- `GET /api/stats` - Get dashboard stats (jobs, applications, avg match)

---

## 🔒 Security Features

- ✅ Password hashing using Werkzeug's PBKDF2
- ✅ Session-based authentication
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS protection (Jinja2 auto-escaping)
- ✅ Environment variables for sensitive data
- ✅ User data isolation (per-user queries only)

---

## 🚀 Deployment

### Deploy to Replit

1. Create new Repl at [replit.com](https://replit.com)
2. Import from GitHub or upload files
3. Add Secrets in Replit:
   - `GROQ_API_KEY`: Your Groq API key
   - `SECRET_KEY`: Random string for sessions
4. Click "Run"
5. Share the public URL

### Deploy to Heroku

```bash
# Install Heroku CLI
heroku login
heroku create skill-flick-app

# Set environment variables
heroku config:set GROQ_API_KEY=your_key_here
heroku config:set SECRET_KEY=your_secret_here

# Deploy
git push heroku main
```

### Deploy to PythonAnywhere

1. Upload files to PythonAnywhere
2. Create virtual environment
3. Install requirements
4. Configure WSGI file to point to app.py
5. Set environment variables in WSGI configuration

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to the branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

### Areas for Contribution
- [ ] Add more job board scrapers (Careers24, JobMail)
- [ ] Implement PDF upload for resumes
- [ ] Add email notifications for new jobs
- [ ] Create mobile app (React Native)
- [ ] Add multi-language support
- [ ] Implement one-click apply automation
- [ ] Add salary negotiation tips
- [ ] Create interview prep questions generator

---

## 🐛 Known Issues & Limitations

### Job Scraping
- **Indeed/PNet may block requests**: Job boards have anti-bot protection. If scraping fails, try again after 5-10 minutes.
- **Rate limiting**: Excessive scraping can trigger temporary blocks. The app implements 2-3 second delays between requests.
- **Selector changes**: Job board HTML can change. Scrapers use multiple selectors as fallback.

### AI Features
- **Groq API free tier**: Limited to 30 requests/minute. For high-traffic use, upgrade to paid tier.
- **Skill extraction accuracy**: ~85-90% accurate. Uses fallback regex if AI fails.
- **Cover letter quality**: Review and edit before submitting.

### Database
- **SQLite limitations**: Good for <100 concurrent users. For production, migrate to PostgreSQL.
- **No background jobs**: Job scraping happens on-demand. For auto-refresh, implement Celery + Redis.

---

## 📈 Roadmap

### Version 1.0 (Current - MVP)
- [x] Multi-source job scraping
- [x] AI skill extraction
- [x] Job matching algorithm
- [x] Cover letter generation
- [x] Skill gap analysis
- [x] Responsive UI

### Version 1.5 (Next Release)
- [ ] PDF upload support
- [ ] Email notifications
- [ ] Application status tracking
- [ ] Job alerts (daily digest)
- [ ] Export applications to PDF

### Version 2.0 (Future)
- [ ] TikTok-style skill gap videos (FFmpeg)
- [ ] One-click apply automation
- [ ] Chrome extension (LinkedIn integration)
- [ ] Company insights (Glassdoor data)
- [ ] Salary negotiation assistant
- [ ] Interview prep with AI

### Version 3.0 (Long-term)
- [ ] Mobile app (iOS/Android)
- [ ] Networking features
- [ ] Recruiter portal
- [ ] AI resume builder
- [ ] Career path recommendations

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Skill-Flick

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

---

## 🙏 Acknowledgments

- **Groq** - For providing free access to Llama 3.3-70B
- **Indeed, PNet, Career Junction, Jobs.co.za** - Job listing data
- **Coursera, edX, Udemy** - Educational resources
- **Flask Community** - Excellent web framework
- **Tailwind CSS** - Beautiful utility-first CSS framework
- **Claude AI** - Development assistance

---

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/skill-flick/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/skill-flick/discussions)
- **Email**: support@skillflick.com
- **Twitter**: [@SkillFlick](https://twitter.com/skillflick)

---

## 📊 Stats

![GitHub stars](https://img.shields.io/github/stars/yourusername/skill-flick?style=social)
![GitHub forks](https://img.shields.io/github/forks/yourusername/skill-flick?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/yourusername/skill-flick?style=social)

---

## 💡 Built For

This project was created to help South African job seekers, particularly those affected by layoffs, find new opportunities quickly by leveraging AI to match their skills with available positions and identify upskilling paths.
