# 🎯 Recursor - AI Lead Scoring Platform

**Recursor** is a comprehensive lead enrichment and scoring platform designed specifically for subscription billing companies like Recurly. It combines AI-powered research, structured scoring templates, team collaboration, and real-time analytics to help sales teams identify and prioritize the highest-potential prospects.

> Built with Recurly's subscription billing market in mind, featuring specialized scoring criteria for SaaS companies, subscription models, and revenue complexity.

---

## 🚀 Why Recursor?

Manual lead research doesn't scale. Generic lead scoring misses the nuances of subscription businesses.

Recursor solves this by:
- **🤖 AI-Powered Research** – Automatically enriches leads with hiring signals, tech stack, and growth indicators
- **📊 Subscription-Focused Scoring** – Custom templates for evaluating subscription billing complexity and revenue sophistication
- **👥 Multi-User Collaboration** – Team-based workflows with role-based permissions (Manager, Account Executive, SDR, Viewer)
- **📈 Performance Analytics** – Track team performance, model effectiveness, and lead quality trends
- **🎯 Professional Dashboard** – Streamlit-based interface perfect for demos and daily workflow

It's:
- **Repeatable** – Structured templates and consistent scoring methodology
- **Auditable** – Every score includes detailed justification and breakdown
- **Collaborative** – Multi-user teams with role-based access control
- **Analytics-Driven** – Comprehensive performance tracking and insights
- **Self-Hosted** – Complete ownership with no vendor dependencies

---

## 📚 Project Architecture

```bash
recursor/
├── dashboard.py       # Streamlit-based UI with multi-user authentication
├── cli.py             # CLI entrypoint for batch processing
├── auth/              # User management and authentication system
│   ├── auth_ui.py      # Login, registration, and profile UI components
│   ├── user_manager.py # User/team management, roles, and permissions
│   └── users.db        # SQLite database for user and team data
├── enrich/            # Web enrichment modules (SerpAPI, hiring signals, tech stack)
├── score/             # GPT scoring with robust API handling and templates
├── analytics/         # Team performance tracking and visualization
├── analysis/          # Lead clustering and segmentation analytics
├── prompts/           # Subscription-focused scoring templates (Recurly-specific)
├── templates/         # Scoring templates, including Recurly-specific criteria
├── data/              # Sample data and demo content for Recurly targets
├── config/            # Configuration files and environment settings
├── scripts/           # Utility scripts for setup and demo data generation
└── README.md
```

---

## 🚀 Quick Start

```bash
# Clone and install dependencies
git clone https://github.com/calebkress/recursor.git
cd recursor
pip install -r requirements.txt

# Add your API keys
cp config/settings.example.py config/settings.py
# Edit config/settings.py with your OpenAI and SerpAPI keys

# Launch the dashboard
streamlit run dashboard.py
```

### 📝 Demo Login
Use any team member email (e.g., `sarah@recursor.com`) with password: `password123`

---

## 🎯 Core Features

### 🔑 **Multi-User Authentication & Teams**
- **Sales-Focused Roles**: Manager, Account Executive, Sales Development Representative, Viewer
- **Team Management**: Create teams, invite members, role-based permissions
- **Secure Authentication**: bcrypt password hashing, JWT sessions, audit logging
- **Demo Team**: Pre-loaded 16-person sales organization across 3 teams

### 🚀 **Live Lead Processing**
- **Real-Time Scoring**: Enter company names and get instant AI-powered scores
- **SerpAPI Integration**: Automatic enrichment with hiring signals, tech stack, news
- **Recurly-Specific Template**: 5-dimension scoring focused on subscription billing needs
- **Multiple AI Models**: Choose from GPT-3.5, GPT-4o-mini, or GPT-4o

### 📈 **Team Analytics & Performance**
- **Performance Tracking**: Sessions, success rates, processing times, lead quality
- **User Comparison**: Individual team member performance metrics
- **Model Analytics**: Compare AI model effectiveness and costs
- **Export Capabilities**: Download reports, session data, and lead analytics

### 🔍 **Advanced Lead Analysis**
- **Clustering Analysis**: Group leads by scoring patterns and characteristics
- **Batch Processing**: Upload CSV files or JSON for bulk analysis
- **Visual Analytics**: Interactive charts, score distributions, priority breakdowns
- **Lead Segmentation**: Identify high-value target segments automatically

---

## 📊 Recurly-Focused Scoring Methodology

The scoring template evaluates leads across 5 key dimensions (20 points each):

1. **Industry Fit** - B2B SaaS, subscription model, recurring revenue
2. **Scale Indicators** - Revenue size, growth trajectory, market position
3. **Platform Maturity** - Technical sophistication and integration needs
4. **Growth & Churn Challenges** - Billing complexity pain points
5. **Revenue Sophistication** - Pricing model complexity and billing requirements

**Sample Output:**
```json
{
  "company": "StreamlineBox",
  "score": 87,
  "priority": "High",
  "justification": "Perfect Recurly fit: B2B SaaS with subscription tiers, growing 20% MoM, manual billing causing 8% involuntary churn",
  "breakdown": {
    "industry_fit": 18,
    "scale_indicators": 17,
    "platform_maturity": 17,
    "growth_churn_challenges": 18,
    "revenue_sophistication": 17
  },
  "summary": [
    "B2B SaaS with tiered subscriptions ($29-299/mo)",
    "Growing 20% MoM, 150K MRR",
    "Manual billing causing 8% involuntary churn"
  ],
  "next_steps": "Schedule demo focused on dunning management and revenue recovery"
}
```

---

## 🛠️ CLI Usage (Advanced)

For power users and automation:

```bash
# Enrich leads with web research
python cli.py enrich --input data/prospects.csv --output data/enriched.json

# Score enriched leads
python cli.py score --input data/enriched.json --output data/scored.json

# Full pipeline in one command
python cli.py full-run --input data/prospects.csv --output data/final_scores.json

# Batch processing with specific models
python cli.py score --input data/enriched.json --model gpt-4o --output results.json
```

---

## Prompt Strategy

Prompts live in `/prompts` as `.txt` templates, with Jinja2-style variables like `{{ company }}` and `{{ enriched_snippets }}`.

Example:

```
You are scoring {{ company }} for fit with Recurly.
Here's what we know:
{{ enriched_snippets }}

Return a JSON object with "summary", "score" (0-100), and "justification".
```

---

## 🗺️ Roadmap

### ✅ **Completed**
- ✅ Multi-user authentication and team management
- ✅ Lead clustering and segmentation analysis
- ✅ Model fallback and retry logic
- ✅ Team performance analytics and reporting
- ✅ Recurly-specific scoring templates
- ✅ Professional dashboard UI suitable for demos

### 🕰️ **Planned**
- [ ] **CRM Integration**: HubSpot API for lead sync and activity tracking
- [ ] **Prompt A/B Testing**: Version management and performance comparison
- [ ] **Advanced Analytics**: Conversion tracking from lead to opportunity
- [ ] **API Endpoints**: REST API for external integrations
- [ ] **Email Sequences**: Automated follow-up based on lead scores
- [ ] **Slack Integration**: Real-time notifications for high-scoring leads

---

## 💼 Perfect for Sales Interviews

This project demonstrates:
- **Technical Skills**: Full-stack development, AI integration, data analytics
- **Sales Understanding**: Subscription billing market knowledge, lead qualification
- **Product Thinking**: User experience design, role-based permissions, team workflows
- **Business Impact**: Measurable improvements to lead quality and team efficiency

Ideal for showcasing during SDR, AE, or Sales Engineer interviews at subscription-focused companies like Recurly.

---

## License

MIT License

---

## Built by Caleb Kress
