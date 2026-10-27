# AI/ML Interview Preparation & Intelligence Platform

> **Source of truth for product requirements.** Saved verbatim from the product owner's
> master prompt on 2026-10-26.
>
> **Note:** the original message was truncated at ~50,000 characters, partway through
> section 30 ("Execution Expectations"); the product owner supplied the remainder in a
> follow-up message, which is merged in below.

## Complete Master Project Prompt

Save this prompt for future use, understand it and use it.

# 1. Your Role and Responsibilities

Act as a highly experienced:

- Senior Software Architect.
- Full-Stack Developer.
- AI/ML Engineer.
- AI Agent Architect.
- Database Architect.
- UI/UX Designer.
- Technical Educator.
- Product Engineer.

Your responsibility is to design and build a complete, production-ready AI/ML Interview Preparation Platform.

Do not just create a prototype, static dashboard, or UI demonstration. Build a fully functional application with a connected frontend, backend, database, authentication system, AI agents, content-generation workflows, and student performance tracking.

Think like an experienced engineering team building a real EdTech product.

Make sensible technical decisions independently. Explain important architectural decisions, identify dependencies, and implement the application incrementally.

Do not unnecessarily complicate the architecture or introduce technologies that do not provide meaningful value.

# 2. Business Context and Product Vision

The platform is intended for an EdTech environment where students learn AI/ML concepts and prepare for technical interviews.

The objective is to help students become interview-ready for roles such as:

- Machine Learning Engineer.
- AI Engineer.
- Data Scientist.
- NLP Engineer.
- Computer Vision Engineer.
- Deep Learning Engineer.
- Generative AI / LLM Engineer.
- Agentic AI Engineer.
- MLOps Engineer.

The platform should combine:

1. Actual interview intelligence.
2. Current industry and market research.
3. Structured AI/ML learning content.
4. Interactive visualizations.
5. Practical Python implementations.
6. Short educational videos.
7. Interview questions and detailed answers.
8. Assessments and revision.
9. Student performance tracking.

The objective is not simply to create another AI/ML learning website.

We want to build an intelligent interview-preparation ecosystem that understands what companies are looking for, converts that information into high-quality educational material, and helps students prepare effectively.

# 3. Two Separate Experiences

The application must have two distinct and securely separated experiences.

## A. Admin Platform

The admin platform is for authorized internal users.

Admins should be able to:

- Configure interview data sources.
- Add and manage source credentials.
- Run the Interview Exploration Agent.
- Run the Market Research Agent.
- Review interview intelligence.
- Analyse market trends.
- Manage AI/ML domains and topics.
- Generate educational content.
- Generate content for individual or multiple topics.
- Review and approve content.
- Publish and update learning material.
- Manage student accounts.
- Monitor student performance.
- Analyse engagement and learning outcomes.
- View agent execution history.
- Manage platform settings.

## B. Student Platform

The student platform is for authenticated learners.

Students should be able to:

- Explore published AI/ML domains.
- Learn individual topics and subtopics.
- Watch educational videos.
- Interact with visualizations.
- Practise Python implementations.
- Prepare using interview questions.
- Complete assessments.
- Revise important concepts.
- Track personal learning progress.
- Understand their strengths and weaknesses.

Students must never see internal agent operations, source credentials, raw interview records, administrative reports, unpublished content, or other students' private information.

This separation must be enforced through backend authorization, not merely by hiding frontend navigation items.

# 4. Overall System Architecture

Design the platform using independent but connected modules.

The major components should include:

1. Admin Authentication and Authorization.
2. Student Authentication and Authorization.
3. Admin Dashboard.
4. Student Dashboard.
5. Interview Data Source Management.
6. Interview Exploration Agent.
7. Market Research Agent.
8. Central Interview Intelligence Database.
9. AI/ML Topic and Content Management.
10. AI Content Generation Engine.
11. Content Review and Publishing Workflow.
12. Student Learning Platform.
13. Assessment Engine.
14. Student Progress and Performance Tracking.
15. Admin Analytics and Reporting.
16. AI Model Integration Layer.
17. Background Job Processing and Monitoring.

Build a modular, scalable, maintainable architecture.

The frontend, backend, database, AI agent services, and external integrations should have clear responsibilities.

# 5. Configurable Interview Data Sources

This is a critical requirement.

The interview data may exist across different websites, portals, private databases, documents, APIs, or other authorized sources.

The links, authentication methods, and credentials may differ between sources. They may also change over time.

**Never hardcode one interview-source URL or assume that all interview data comes from a single website.**

## Admin-managed Interview Data Sources

Create a dedicated admin section called **Interview Data Sources**.

The admin must be able to:

- Add a new interview-source URL.
- Edit an existing URL.
- Enable or disable a source.
- Remove a source.
- Provide a username and password where required.
- Configure API keys, access tokens, or other authentication details.
- Select or configure the appropriate authentication method.
- Test the connection.
- View connection status.
- View the last successful synchronization.
- View the last attempted synchronization.
- Select one or multiple sources for exploration.
- Trigger the Interview Exploration Agent.
- Review extraction results and errors.

Support multiple independent data sources.

For example:

- Source A may require username and password.
- Source B may require an API key.
- Source C may provide authorized document access.
- Source D may use a different authentication mechanism.

These are examples. Build an extensible integration layer rather than limiting the system to these examples.

## Secure Credential Management

- Never hardcode credentials in source code.
- Never expose credentials in frontend code or API responses.
- Never store passwords in plaintext.
- Use secure secret storage and encryption.
- Use environment variables or a managed secrets service for application-level secrets.
- Restrict credential access to authorized backend services.
- Never expose source credentials to students.
- Do not include credentials in logs or agent reports.
- Support credential rotation and updates without changing application code.

Respect source permissions, terms of service, and access restrictions.

Do not bypass CAPTCHA, MFA, paywalls, or other security mechanisms.

If automated access is not supported, provide authorized alternatives such as manual file uploads, document imports, or API integrations.

## Source Exploration Workflow

The workflow should be:

1. Admin opens Interview Data Sources.
2. Admin adds or selects a source.
3. Admin provides or updates its credentials.
4. The application validates the connection.
5. Admin selects the source to explore.
6. Admin manually triggers the Interview Exploration Agent.
7. The agent accesses authorized information.
8. It extracts relevant interview experiences and questions.
9. It structures the extracted information.
10. It identifies duplicates and new records.
11. It generates an extraction report.
12. Admin reviews the results.
13. Approved information is stored in the central intelligence database.

The agent should support incremental exploration so that previously processed information is not repeatedly extracted unnecessarily.

Maintain source-specific synchronization history, timestamps, extraction status, and error reports.

When a new URL or source is configured, the admin must be able to explore it without requiring a developer to modify the code.

# 6. Interview Exploration Agent

Develop an independent AI agent responsible for exploring configured interview sources.

Its responsibilities include:

- Accessing authorized configured sources.
- Discovering interview experiences.
- Extracting interview questions.
- Identifying companies and job roles.
- Identifying interview rounds.
- Extracting dates and technologies where available.
- Identifying frequently occurring topics.
- Detecting repeated or similar questions.
- Categorizing questions into appropriate domains and subtopics.
- Identifying technical skills tested during interviews.
- Identifying new records since the previous exploration.
- Producing structured reports.

For every extracted interview question, preserve its provenance.

Where available, store:

- Original source.
- Source URL.
- Source record identifier.
- Company.
- Job role.
- Interview round.
- Interview date or approximate period.
- Original question.
- Topic and subtopic.
- Technologies involved.
- Difficulty level, if supported.
- Extraction timestamp.
- Verification status.
- Source confidence.

Do not fabricate interview experiences.

Do not represent AI-generated questions as actual interview questions.

## Manual Execution

The Interview Exploration Agent must run only when explicitly triggered by an authorized admin.

It must not automatically run:

- When a student logs in.
- When an admin opens the dashboard.
- When a topic is opened.
- When a student visits the learning platform.

The admin should control when exploration happens.

Provide a clear execution history, progress status, error reporting, and retry functionality.

# 7. Market Research Agent

Develop a separate AI agent to research the current AI/ML job market.

The objective is to understand what skills, technologies, and concepts are currently relevant to AI/ML engineering roles.

The agent should research:

- Current AI/ML job descriptions.
- Frequently requested technical skills.
- Emerging technologies.
- Common interview expectations.
- Role-specific requirements.
- Industry hiring trends.
- Commonly tested technical concepts.
- Changes in technology demand.
- Relevant interview questions.

Use credible, current, and traceable sources.

## Research Output

Generate structured research reports containing:

- Topic or technology.
- Relevant job roles.
- Current industry relevance.
- Skill-demand observations.
- Supporting evidence.
- Source references.
- Research date.
- Suggested interview questions.
- Recommendations for the learning curriculum.
- Topics that may need updating or deprioritization.

## Strict Restriction: Research Does Not Mean Content Generation

The Market Research Agent must never automatically generate learning content.

For example, if it discovers that Agentic AI is becoming increasingly relevant, it may recommend:

"Agentic AI should be added to the learning curriculum because of increasing industry relevance."

It must not automatically generate the topic's explanations, questions, videos, or assessments.

Only an authorized admin can approve the recommendation and initiate content generation.

The same restriction applies to information extracted by the Interview Exploration Agent.

Research and exploration provide intelligence. They do not independently publish content or trigger unrestricted content-generation workflows.

# 8. Combined Interview Intelligence Engine

Build a central intelligence layer that combines the outputs of both agents.

It should connect:

- Actual interview questions.
- Interview patterns.
- Market research.
- Current technology demand.
- AI/ML domains.
- Topics and subtopics.
- Generated interview questions.
- Published learning material.

Clearly distinguish four types of questions:

1. **Actual Interview Questions:** Extracted from an authorized interview source.
2. **AI-Generated Interview Questions:** Generated using actual interview patterns.
3. **Research-Derived Questions:** Generated based on current industry requirements.
4. **Admin-Created Questions:** Manually added by authorized admins.

Maintain this classification in the database.

The intelligence engine should help admins understand:

- Which topics are frequently asked?
- Which topics are becoming more relevant?
- Which topics are declining in relevance?
- Which skills are important for specific roles?
- Which topics need additional content?
- Which questions are repeated?
- Which concepts appear across multiple job roles?
- Which topics should be prioritized for students?

Do not use historical interview frequency alone to determine current topic importance.

Combine historical interview data with current market research.

Do not fabricate question frequency, industry demand, or interview patterns.

# 9. AI/ML Learning Taxonomy

Create a structured, expandable AI/ML learning taxonomy.

The initial taxonomy should cover the following domains.

## Mathematics and Statistics

- Linear Algebra.
- Probability.
- Statistics.
- Calculus.
- Optimization.

## Machine Learning

- Supervised Learning.
- Unsupervised Learning.
- Regression.
- Classification.
- Clustering.
- Dimensionality Reduction.
- Ensemble Learning.
- Model Evaluation.

## Deep Learning

- Neural Network Fundamentals.
- Activation Functions.
- Backpropagation.
- Optimizers.
- CNNs.
- RNNs.
- Transformers.

## Computer Vision

- Image Processing.
- Object Detection.
- Image Classification.
- Image Segmentation.
- Transfer Learning.

## Natural Language Processing

- Text Preprocessing.
- TF-IDF.
- Word Embeddings.
- Sequence Models.
- Attention.
- Transformers.

## Generative AI and LLMs

- LLM Fundamentals.
- Tokenization.
- Embeddings.
- Fine-tuning.
- LoRA.
- RAG.
- Vector Databases.
- LLM Evaluation.

## Agentic AI

- AI Agents.
- Tool Calling.
- Planning.
- Multi-Agent Systems.
- LangGraph.
- Agent Evaluation.

## MLOps

- Model Deployment.
- Model Monitoring.
- Experiment Tracking.
- CI/CD.
- Model Serving.

This taxonomy should be expandable and editable through the admin platform.

Admins must be able to add domains, topics, and subtopics without modifying application code.

# 10. Controlled Initial Content Rollout

Do not immediately generate content for every domain and topic.

This is a very important requirement.

Initially, develop only:

- 2–3 major domains.
- 2–3 subtopics within each selected domain.

For example:

**Machine Learning**

- Supervised vs Unsupervised Learning.
- Linear Regression.
- Logistic Regression.

**Deep Learning**

- Neural Network Fundamentals.
- Activation Functions.
- Gradient Descent.

**Natural Language Processing**

- Text Preprocessing.
- TF-IDF.
- Word Embeddings.

These are initial examples, not mandatory selections.

The final selection should be informed by actual interview intelligence and current market research.

Develop the initial topics completely.

Evaluate:

- Content quality.
- Technical correctness.
- Educational clarity.
- Interview relevance.
- Visualization quality.
- Python implementation quality.
- Video quality.
- Assessment quality.
- Overall student experience.

Only after the admin reviews the initial output and provides an explicit green signal should content generation expand to additional topics.

## Individual and Bulk Generation

Support both:

**Individual generation:** Select one topic and generate its learning content.

**Bulk generation:** Select multiple topics and initiate content generation for the entire selection.

The bulk workflow must:

- Show selected topics.
- Allow component-level selection.
- Display progress for each topic.
- Show successful and failed jobs.
- Support retries.
- Allow individual topic review.
- Never publish the entire batch automatically.

Market research recommendations must not bypass admin approval.

---

# AI/ML Interview Preparation & Intelligence Platform

## Complete Master Project Prompt — Part 2 of 2

# 11. Topic Learning Experience

Every published topic should provide a complete, structured, interview-oriented learning experience.

The learning experience should not be limited to lengthy theoretical explanations.

Students should understand concepts through explanations, practical examples, interactive visualizations, videos, Python implementations, interview questions, and assessments.

## A. Concept Explanation

For every topic:

- Start with simple intuition.
- Explain why the concept is important.
- Introduce technical terminology progressively.
- Use relatable real-world examples.
- Explain the underlying mathematics where necessary.
- Connect theory to practical applications.
- Highlight common misunderstandings.
- Explain the concept from an interview perspective.

The content should be understandable to students with different levels of technical knowledge.

Avoid unnecessary complexity and overly lengthy explanations.

## B. Interactive Visualizations

Provide interactive visualizations and playgrounds wherever they improve conceptual understanding.

Use this as a reference for the expected experience:

https://www.aimlverse.in/visuals/gradient-descent

Examples:

- Gradient Descent playground.
- K-Means clustering visualization.
- Linear Regression visualization.
- Decision Tree visualization.
- Neural Network forward propagation.
- CNN feature-map visualization.
- Attention mechanism visualization.
- PCA visualization.

Visualizations should be interactive, allowing students to change parameters and observe how the output changes.

Do not simply embed static images and call them interactive visualizations.

Build reusable visualization components wherever possible.

## C. Short AI-Generated Educational Videos

Provide short educational videos, ideally 3–4 minutes per concept.

Videos should:

- Explain one concept at a time.
- Use simple language.
- Follow a logical teaching sequence.
- Include relevant visual explanations.
- Use examples and demonstrations.
- Focus on interview-relevant takeaways.

The content-generation workflow should support:

1. Video script generation.
2. Scene planning.
3. Visual asset generation.
4. Narration or text-to-speech.
5. Video assembly.
6. Preview and review.
7. Publishing.

Actual instructor-recorded videos can be introduced as a future feature.

Do not block the initial platform development on instructor video availability.

## D. Practical Python Implementation

Include working Python implementations.

Every relevant topic should provide:

- Required libraries.
- Dataset or input example.
- Step-by-step implementation.
- Executable code.
- Output examples.
- Code explanations.
- Common mistakes.
- Practical applications.

The code must be tested before publication.

Where practical, provide an interactive code playground or a suitable execution environment with appropriate security restrictions.

Never execute arbitrary student code directly on the main application server without isolation and resource limits.

## E. Interview Preparation

For every topic, provide:

- Basic interview questions.
- Intermediate interview questions.
- Advanced interview questions.
- Conceptual questions.
- Mathematical questions where relevant.
- Coding questions.
- Scenario-based questions.
- Practical implementation questions.
- Follow-up questions.
- Detailed answers.
- Important interview takeaways.

Explain not only the answer but also what an interviewer expects the student to understand.

## F. Quick Revision

Provide concise revision material:

- Important definitions.
- Key formulas.
- Comparison tables.
- Important concepts.
- Common mistakes.
- Frequently confused topics.
- Interview takeaways.

A student should be able to revise an individual topic in approximately five minutes.

## G. Assessments

Include:

- Multiple-choice questions.
- Conceptual questions.
- Coding questions where relevant.
- Scenario-based questions.
- Difficulty levels.
- Correct answers.
- Detailed explanations.

Assessments should test understanding rather than just memorization.

# 12. Interview Intelligence Inside Learning Topics

Integrate actual interview intelligence into the appropriate published topics.

Students should understand which concepts are commonly tested and what kinds of questions they should prepare for.

However, apply a strict company-privacy and anonymization policy.

## Student-Facing Company-Name Restriction

By default, do not expose the name of the company associated with an extracted interview question.

For example, do not display:

"Company ABC asked this question in its Machine Learning Engineer interview."

Instead, display:

"This question has appeared in actual Machine Learning Engineer interviews."

The student-facing interface may show:

- Question.
- Job role, where appropriate.
- Interview round, where appropriate.
- Difficulty.
- Topic.
- Relevance indicators.
- Frequency indicators, if supported by sufficient evidence.

Do not include company names in question-card titles, badges, labels, metadata, source descriptions, or other student-facing UI elements.

Do not insert company names into original question wording when they are not part of the question.

If the company name is essential to the original question, apply a configurable anonymization policy while preserving the question's meaning.

## Admin-Facing Interview Intelligence

Authorized admins must be able to inspect the complete original interview record, including:

- Company name.
- Job role.
- Interview date.
- Interview round.
- Original question.
- Source URL.
- Source context.
- Extraction status.
- Verification status.
- Frequency information.

Maintain the original source data for auditing and verification.

The system must never falsely claim that a company asked a question or exaggerate the frequency of a question.

# 13. Separate Admin and Student Authentication

Implement two distinct credential types and experiences.

## A. Admin Authentication

Create a dedicated admin login.

Admin accounts should use their assigned admin credentials.

Admin capabilities include:

- Managing interview data sources.
- Managing source credentials.
- Running AI agents.
- Viewing internal reports.
- Managing topics.
- Generating learning content.
- Reviewing and publishing content.
- Managing students.
- Viewing student performance.
- Accessing platform analytics.
- Managing platform settings.

Support role-based admin permissions.

For example, different authorized roles may have access to content review, student analytics, or platform configuration.

Do not assume every admin should automatically have unrestricted access.

## B. Student Authentication

Create a separate student login and registration experience.

Students should use their own credentials.

Implement:

- Secure registration.
- Login and logout.
- Password hashing.
- Session management.
- Password reset.
- Account status management.
- Appropriate access controls.

A student should be able to log in from different devices and continue learning from their previous progress.

## C. Strict Authorization

Implement role-based access control on the backend.

Do not rely only on frontend navigation restrictions.

Ensure:

- Students cannot access admin APIs.
- Students cannot access internal interview records.
- Students cannot access source credentials.
- Students cannot access agent reports.
- Students cannot access unpublished content.
- Students cannot view other students' records.
- Admin access is limited according to assigned permissions.

Test unauthorized API access explicitly.

# 14. Persistent Student Data and Performance Tracking

This is a core requirement.

Every registered student must have a persistent account and a unique student ID.

The system must store learning activity and performance against that student ID.

Do not treat student progress as temporary browser state.

When a student logs in, retrieve their existing learning history from the database.

Whenever a student interacts with the platform, store relevant learning and performance information.

## Student Profile

Store:

- Unique student ID.
- Name.
- Email or registered identifier.
- Account status.
- Registration date.
- Last login.
- Assigned cohort or learning group, where applicable.

## Learning Activity

Track:

- Topics visited.
- Subtopics completed.
- Topics completed.
- Videos watched.
- Practical exercises completed.
- Assessments attempted.
- Revision activity.
- Learning milestones.
- Time spent learning, where measurable.

## Assessment Performance

Store:

- Assessment ID.
- Attempt ID.
- Questions attempted.
- Correct answers.
- Incorrect answers.
- Score.
- Percentage.
- Difficulty.
- Time taken.
- Attempt timestamp.
- Individual question responses.
- Historical attempts.

Do not overwrite historical attempts when a student retakes an assessment.

## Interview Preparation Performance

Track:

- Interview questions attempted.
- Questions answered correctly.
- Topic-wise question performance.
- Weak topics.
- Strong topics.
- Practice-test results.
- Progress over time.

## Performance Analytics

Calculate:

- Overall learning progress.
- Domain-wise completion.
- Topic-wise completion.
- Assessment accuracy.
- Average assessment score.
- Strong and weak topics.
- Improvement over time.
- Learning activity trends.

Do not rely on a single score to represent a student's overall knowledge.

Provide meaningful indicators that distinguish content completion from actual assessment performance.

## Persistent Data Storage

Use a proper database to store student information.

Design suitable models for:

- Users.
- Roles and permissions.
- Student profiles.
- Topics and subtopics.
- Published content.
- Learning progress.
- Assessment questions.
- Assessment attempts.
- Individual responses.
- Performance summaries.
- Login and activity records.

The information must remain available after logout, across devices, and across future sessions.

# 15. Admin Dashboard — Student Performance and Platform Analytics

The performance-monitoring dashboard is an **admin-side feature**.

This is separate from the student dashboard.

The admin dashboard should provide a comprehensive view of platform activity and student performance.

## Admin Overview

Display:

- Total registered students.
- Active students.
- New registrations.
- Student engagement.
- Overall learning progress.
- Domain-wise completion.
- Assessment performance.
- Completion rates.
- Students requiring attention.

## Student Management

Admins should be able to:

- View the student list.
- Search and filter students.
- Open individual student profiles.
- View their learning history.
- Inspect topic-wise progress.
- View assessment history.
- Identify strong and weak topics.
- Compare assessment attempts.
- Identify inactive students.
- Identify students requiring additional support.

## Platform Analytics

Provide charts and reports for:

- Student registration trends.
- Active versus inactive students.
- Topic completion rates.
- Domain-wise performance.
- Assessment score distributions.
- Learning engagement trends.
- Weak-topic analysis.
- Cohort-level performance, where applicable.

Allow filtering by:

- Date range.
- Domain.
- Topic.
- Student.
- Cohort.

Provide export options for authorized admins.

Protect all student information with appropriate permissions and privacy controls.

---

### AI-Powered Student Performance Intelligence & Role-Based Candidate Ranking

Build an AI-powered Student Performance Intelligence Agent that continuously analyzes students' learning activity, assessment performance, technical knowledge, practical implementation skills, and interview preparation progress.

The objective is to help administrators understand which students are performing well and which students demonstrate strong readiness for specific AI/ML engineering roles.

**1. Role-Based Top 10 Student Ranking**

- Provide an admin dashboard where administrators can select a target role, such as:
    - Machine Learning Engineer
    - AI Engineer
    - Data Scientist
    - NLP Engineer
    - Computer Vision Engineer
    - Deep Learning Engineer
    - Generative AI / LLM Engineer
    - Agentic AI Engineer
    - MLOps Engineer
- Based on the selected role, analyze student performance against the technical skills, knowledge areas, practical capabilities, and interview requirements relevant to that role.
- Generate a ranked list of the top 10 students who demonstrate the strongest readiness for the selected role.
- Allow administrators to view more than the top 10 when needed, including the complete student list and relevant filters.

**2. AI-Generated Candidate Summary**

For every student in the top 10 list, generate a short AI-written summary explaining:

- Why the student appears in the ranking.
- Their strongest technical skills and knowledge areas.
- Their assessment scores and consistency.
- Their practical coding and project performance, where available.
- Their interview preparation progress.
- Their weak areas or skills that still require improvement.
- How closely their demonstrated skills align with the selected role.

The summary should be concise, evidence-based, and understandable without requiring administrators to inspect every individual performance metric.

**3. Individual AI Student Performance Report**

When an administrator clicks on a particular student, provide a detailed AI-generated performance report containing:

- Student profile and learning history.
- Overall learning progress and topic-wise completion.
- Technical skills and role-specific competency analysis.
- Assessment history, scores, accuracy, and improvement trends.
- Strong and weak technical areas.
- Practical implementation and coding performance.
- Interview question-solving performance.
- Areas requiring additional preparation.
- Role-specific readiness assessment.
- Recommended next steps to improve interview readiness.

The report should explain why the student is considered ready, partially ready, or requires further preparation for the selected role. Every conclusion should be supported by actual student performance data.

**4. Role-Specific Candidate Comparison**

Administrators should be able to:

- Select a target role and compare students against its requirements.
- View the top 10 candidates and their individual readiness summaries.
- Compare students across technical skills, assessment performance, practical capabilities, and interview preparation.
- Open any student's complete profile and AI-generated report.
- Filter students by cohort, learning progress, assessment performance, and other relevant criteria.

**5. AI Evaluation and Ranking Methodology**

- Develop a configurable role-specific evaluation framework.
- Consider multiple factors rather than ranking students using only assessment scores or course completion.
- Use measurable evidence such as topic mastery, assessment accuracy, coding performance, practical projects, consistency, and interview practice results.
- Make the evaluation criteria and relative importance of each factor transparent to administrators.
- Clearly distinguish measured performance from AI-generated interpretations.
- Generate rankings only when sufficient student data is available. Mark insufficient-data cases rather than making unsupported predictions.
- Allow administrators to review, challenge, and override AI-generated assessments.
- Treat the ranking as an interview-readiness indicator, not a guarantee of selection or actual hiring success.

**6. Admin Access to All Student Profiles**

Administrators must be able to access the complete student directory, not just the top 10 candidates.

Each student profile should provide:

- Personal and academic information available to the platform.
- Learning progress and activity history.
- Assessment and interview preparation performance.
- Strengths, weaknesses, and improvement trends.
- Role-specific readiness reports.
- Historical AI evaluations and ranking changes.

The AI agent should periodically update performance analysis when meaningful new student data becomes available, while administrators should also have the option to trigger a manual analysis.

All reports, rankings, and student information must remain strictly admin-only. Students must never be able to access other students' profiles, rankings, or performance reports.

# 16. Student Dashboard

The student dashboard is a personal learning dashboard.

Students should only see their own information.

Include:

- Welcome section.
- Overall learning progress.
- Available AI/ML domains.
- Continue-learning section.
- Completed topics.
- Pending topics.
- Recent assessment scores.
- Personal strengths and weaknesses.
- Recommended next learning topics.
- Interview preparation progress.

Do not display:

- Other students' performance.
- Aggregate administrative analytics.
- Interview-source URLs.
- Company-specific interview records.
- Agent reports.
- Admin controls.
- Unpublished content.

# 17. Admin Content Generation Studio

Create a dedicated admin interface for generating learning content.

The admin should be able to:

1. Select a domain.
2. Select one or multiple topics.
3. Select subtopics.
4. Choose which content components to generate.
5. Select relevant interview intelligence and research context.
6. Start content generation.
7. Monitor generation progress.
8. Review generated content.
9. Edit or regenerate individual sections.
10. Run quality checks.
11. Approve and publish content.

## Bulk Generation

Support content generation for multiple topics in a single operation.

For example, an admin may select:

- Linear Regression.
- Logistic Regression.
- Decision Trees.
- Random Forest.

The system should process the selected topics as separate jobs within a bulk operation.

Show:

- Selected topics.
- Job status.
- Generation progress.
- Successful jobs.
- Failed jobs.
- Retry options.
- Review status.

Do not automatically publish a bulk batch.

Each topic must be independently reviewable.

## Selectable Content Components

Allow generation of individual components or combinations of:

- Concept explanations.
- Practical examples.
- Python implementations.
- Interview questions.
- Detailed answers.
- Follow-up questions.
- Revision notes.
- Assessments.
- Interactive visualization specifications.
- Video scripts.
- AI-generated educational videos.

Support regenerating an individual component without regenerating the entire topic.

# 18. Content Review and Publishing

Implement a controlled content lifecycle:

**Draft → Under Review → Approved → Published → Archived**

Only authorized admins can approve and publish content.

Admins must be able to:

- Review content.
- Edit content.
- Reject content.
- Regenerate specific sections.
- Compare content versions.
- Restore earlier versions.
- Unpublish content.
- Archive content.

Maintain content version history.

Only published and approved content should be accessible to students.

# 19. User Interface and Experience

Build a modern, professional, responsive application.

The interface should be intuitive, visually consistent, and suitable for an EdTech product.

## Admin Navigation

Provide navigation for:

- Overview.
- Interview Data Sources.
- Interview Exploration Agent.
- Market Research Agent.
- Interview Intelligence.
- Domains and Topics.
- Content Generation Studio.
- Content Review and Publishing.
- Student Management.
- Student Performance Analytics.
- Agent Execution History.
- System Settings.

## Student Navigation

Provide navigation for:

- Dashboard.
- Explore AI/ML.
- Learning Paths.
- Interview Preparation.
- Practice Assessments.
- Revision.
- My Progress.
- My Profile.

Use:

- Consistent design system.
- Accessible typography.
- Responsive layouts.
- Clear visual hierarchy.
- Meaningful charts.
- Loading states.
- Empty states.
- Error states.
- Useful feedback messages.

Do not create a generic dashboard just to make the interface look impressive. Every screen should serve a clear user purpose.

# 20. Technical Architecture and Engineering

Select a suitable production-ready technology stack.

Make technical decisions based on:

- Maintainability.
- Performance.
- Scalability.
- Security.
- Developer experience.
- AI integration.
- Deployment requirements.

Build clear separation between:

- Frontend.
- Backend.
- Database.
- AI agents.
- Background workers.
- External integrations.
- File and media storage.

Implement:

- API validation.
- Error handling.
- Logging.
- Background job processing.
- Database migrations.
- Authentication and authorization.
- Rate limiting.
- Caching where appropriate.
- Secure configuration.
- Automated testing.

Avoid unnecessary dependencies and architectural complexity.

Do not introduce technologies merely because they are popular.

---

### Platform Speed and Responsiveness

- The platform must be fast, responsive, and optimized for a smooth user experience.
- Pages, dashboards, student profiles, and learning content should load quickly.
- Use pagination, lazy loading, caching, optimized database queries, and asynchronous processing wherever appropriate.
- Long-running AI tasks must never block the main application or make the interface unresponsive.
- Optimize interactive visualizations, videos, and learning components for smooth performance.
- Ensure the platform remains responsive under concurrent usage by thousands of students.
- Avoid unnecessary API calls, repeated database queries, and redundant AI model invocations.

## AI Model Provider Abstraction

Keep AI integrations modular.

The application should not be permanently dependent on one AI provider.

Support an abstraction layer that allows different models or providers to be selected for:

- Research.
- Interview question generation.
- Educational content generation.
- Content evaluation.
- Classification.
- Summarization.

Use suitable models for individual tasks rather than using the most expensive model for everything.

The model used to develop the application should not be hardcoded as the only model available to the deployed product.

# 21. Agent Reliability and Execution Management

Interview Exploration and Market Research must have independent execution workflows.

Implement:

- Manual triggering.
- Job status tracking.
- Progress reporting.
- Retry handling.
- Error reporting.
- Execution history.
- Source-specific configuration.
- Structured output validation.
- Human approval checkpoints.

Handle:

- Authentication failures.
- Source unavailability.
- Partial extraction.
- Duplicate records.
- API errors.
- Model errors.
- Rate limits.
- Interrupted jobs.

Normal student activity must never trigger administrative agent workflows.

# 22. Database and Knowledge Base Design

Design the database before implementing dependent features.

Include appropriate models and relationships for:

- Admin users.
- Student users.
- Roles and permissions.
- Interview data sources.
- Encrypted source credentials or secret references.
- Extracted interview records.
- Research reports.
- Domains.
- Topics.
- Subtopics.
- Content versions.
- Published learning material.
- Generated questions.
- Assessments.
- Student learning progress.
- Student assessment attempts.
- Individual question responses.
- Performance analytics.
- Agent jobs.
- Execution logs.

Maintain relationships between:

- Interview questions and their original sources.
- Interview questions and topics.
- Research recommendations and topics.
- Generated questions and their generation source.
- Learning content and its supporting intelligence.
- Students and their learning activity.

Preserve provenance and version history.

Use appropriate indexes, constraints, relationships, and database migrations.

# 23. AI Content Quality and Evaluation

All generated material must be technically accurate, educationally useful, and relevant to interview preparation.

Implement quality checks for:

- Factual correctness.
- Conceptual clarity.
- Mathematical consistency.
- Code execution.
- Question-answer alignment.
- Duplicate questions.
- Difficulty classification.
- Topic relevance.
- Interview relevance.
- Broken references and links.
- Video script quality.
- Visualization correctness.

Use automated checks where practical and human review for important content.

Do not claim content is verified merely because an AI model generated it.

Maintain clear distinctions between verified source material and generated educational content.

# 24. Cost and Performance Management

Build the platform with cost awareness.

Monitor:

- Input tokens.
- Output tokens.
- Model usage.
- Cost per agent.
- Cost per content-generation job.
- Cost per topic.
- Cost per bulk-generation batch.
- Failed and retried requests.
- Infrastructure usage.

Implement configurable limits for bulk generation.

Use background processing for long-running jobs.

Avoid unnecessarily repeating expensive AI operations.

Use caching where appropriate.

Design the application to scale without making every student interaction dependent on expensive model calls.

# 25. Security, Privacy, and Data Protection

Security must be considered from the beginning.

Implement:

- Secure authentication.
- Backend-enforced role-based authorization.
- Password hashing.
- Encrypted secrets.
- Secure session management.
- API rate limiting.
- Input validation.
- Access control.
- Audit logging.
- Secure file handling.
- Student data isolation.
- Appropriate data retention policies.

Pay special attention to the separation between admin, student, and interview-source credentials.

Sensitive interview-source information must never be available to student accounts.

Do not expose private student data to unauthorized users.

Maintain an audit trail for important admin actions, such as publishing content, changing source credentials, running agents, and modifying student records.

# 26. Testing and Deployment

Include:

- Frontend tests.
- Backend tests.
- API tests.
- Database tests.
- Authentication tests.
- Authorization tests.
- Agent integration tests.
- Content-generation tests.
- Student-data isolation tests.
- End-to-end tests.

Explicitly verify:

1. Students cannot access admin routes or APIs.
2. One student cannot access another student's records.
3. Admin credentials are never exposed.
4. Interview-source credentials are never exposed.
5. Unpublished content is inaccessible to students.
6. Student performance persists across sessions and devices.
7. Agent jobs do not run automatically during student login.
8. Bulk generation handles errors and retries.
9. Company names are not exposed in student-facing interview question displays by default.
10. Only authorized admins can access original company and source information.

Prepare deployment documentation covering:

- Environment setup.
- Database configuration.
- Secrets management.
- Database migrations.
- Background workers.
- File and media storage.
- Monitoring.
- Logging.
- Backups.
- Production deployment.

Keep the application runnable throughout development.

# 27. Development Phases

Build the application in controlled phases.

## Phase 1: Architecture and Foundation

- Inspect the existing project.
- Define the architecture.
- Select the technology stack.
- Set up frontend and backend.
- Configure the database.
- Implement admin authentication.
- Implement student authentication.
- Implement role-based authorization.
- Create initial dashboards and navigation.

## Phase 2: Configurable Interview Data Sources

- Build Interview Data Sources.
- Implement secure credential management.
- Support multiple sources.
- Implement connection validation.
- Build extraction and import infrastructure.

## Phase 3: Intelligence Agents

- Implement Interview Exploration Agent.
- Implement Market Research Agent.
- Build execution history and reports.
- Create the central intelligence database.
- Implement manual triggering and human approval.

## Phase 4: Initial Learning Content

- Select 2–3 domains.
- Select 2–3 subtopics within each.
- Implement content generation.
- Build learning pages.
- Add interactive visualizations.
- Add Python implementations.
- Add educational video workflows.
- Add interview questions and assessments.
- Test the initial student learning experience.

## Phase 5: Content Review and Expansion

- Implement content quality checks.
- Build admin review and publishing.
- Support individual generation.
- Support bulk generation.
- Obtain explicit approval before expanding.

## Phase 6: Student Performance System

- Implement persistent learning progress.
- Store assessment attempts.
- Calculate performance indicators.
- Build admin-side student analytics.
- Build personal student progress dashboards.

## Phase 7: Production Readiness

- Complete testing.
- Optimize performance.
- Review security.
- Implement deployment infrastructure.
- Add monitoring.
- Add backups.
- Complete documentation.

Do not skip foundational phases just to build visually impressive features quickly.

# 28. Non-Negotiable Requirements

1. Build a functional application, not just a prototype.
2. Support configurable interview-source URLs.
3. Support different credentials and authentication methods for different sources.
4. Store credentials securely.
5. Support multiple interview data sources.
6. Allow admins to trigger interview exploration manually.
7. Allow admins to trigger market research manually.
8. Never automatically generate content from agent research.
9. Keep actual and AI-generated questions distinguishable.
10. Preserve the provenance of interview questions.
11. Begin with only 2–3 domains and 2–3 subtopics within each.
12. Wait for explicit admin approval before expanding content.
13. Support individual and bulk content generation.
14. Provide an admin-only content-generation studio.
15. Require human review before publishing.
16. Never expose internal agent operations to students.
17. Do not expose source company names in student-facing interview question displays by default.
18. Keep original company and source information available to authorized admins.
19. Implement separate admin and student authentication.
20. Store student learning and assessment history persistently.
21. Provide student-specific progress dashboards.
22. Provide admin-side student performance analytics.
23. Enforce backend role-based access control.
24. Protect student data from cross-account access.
25. Keep the platform modular, scalable, secure, and maintainable.
26. Monitor AI usage and infrastructure costs.
27. Implement automated testing and production deployment practices.
28. Never fabricate actual interview questions, sources, company associations, or frequency statistics.
29. Preserve content version history.
30. Support reliable background processing and retry mechanisms.
31. Keep the platform usable even when optional AI services are unavailable.
32. Maintain a clear distinction between research recommendations and approved curriculum decisions.

# 29. What Success Looks Like

Imagine a student preparing for an AI Engineer interview.

They open the platform.

They see the most important published AI/ML topics based on real interview patterns and current market requirements.

They select Machine Learning.

They open K-Means Clustering.

Instead of reading a lengthy theoretical explanation, they first understand the concept through a simple example.

They watch a 3-minute explanation.

They interact with a visualization and see how clusters form.

They implement the algorithm using Python.

They then practise questions that companies have actually asked, along with additional questions generated from current market research.

They understand what the interviewer expects and can revise the topic in five minutes before an interview.

Their learning progress and assessment performance are automatically saved to their account.

When they log in again, they can continue from where they stopped.

They can identify their strengths and weaknesses and work on topics that require improvement.

Separately, an administrator can log in, explore new interview information, research industry changes, select recommended topics, generate learning content in bulk, review it, and publish it.

The administrator can also monitor student engagement, inspect individual student performance, identify learning gaps, and understand how effectively students are preparing.

Students never need to know about these internal agent operations.

They simply receive an updated, high-quality learning experience.

**This is the learning experience we want to create.**

The ultimate objective is not simply to teach students AI/ML. It is to make them interview-ready for real AI/ML engineering roles.

# 30. Your First Task

Before starting implementation:

1. Analyze the complete project environment.
2. Understand all the requirements in both parts of this prompt.
3. Inspect the existing codebase, dependencies, and implementation status.
4. Identify the architecture and major modules.
5. Propose the most suitable technology stack.
6. Explain why the selected technologies are appropriate.
7. Design the database structure and relationships.
8. Define the admin and student authentication architecture.
9. Define the role-based authorization model.
10. Define the responsibilities and communication flow of both AI agents.
11. Define the configurable interview-source integration and credential-management approach.
12. Define the content-generation and approval workflows.
13. Define the student performance data model.
14. Define the initial student and administrator user journeys.
15. Identify missing information, dependencies, and external integrations.
16. Identify the first 2–3 domains and 2–3 subtopics within each for initial content quality evaluation.
17. Define how the initial content will be tested, reviewed, and approved before scaling.

After presenting this plan, begin implementing Phase 1.

## Execution Expectations

Do not spend excessive time producing documentation without building anything.

Start by understanding the existing project and then move towards implementation.

Work incrementally.

For each major milestone:

- Implement working functionality.
- Run relevant tests.
- Identify and fix errors.
- Explain what has been completed.
- Identify what remains.
- Mention any external dependency that requires my input.
- Keep the application runnable.

Do not claim a feature is complete unless it has actually been implemented and tested.

Do not create placeholder buttons or disconnected UI elements and represent them as completed functionality.

Do not skip database, backend, or security implementation in favour of frontend appearance.

Do not generate all AI/ML learning content immediately.

Wait for explicit approval before expanding beyond the initial content evaluation batch.

Ask for additional information only when genuinely required.

When interview-source URLs and credentials are provided later, integrate them through secure configuration. Do not wait for these credentials to build the rest of the application.

Make reasonable assumptions for independent implementation work and clearly document them.

## Final Product Vision

Think of this as building a real EdTech product that can eventually serve thousands of AI/ML students preparing for placements.

The final product must have two connected but securely separated experiences:

**Admin:** Configure data sources, manage credentials, explore interview intelligence, conduct market research, manage the knowledge base, generate and publish content, manage students, and analyse student performance.

**Students:** Learn AI/ML concepts, explore interactive visualizations, watch short educational videos, implement Python examples, practise actual-pattern-based and research-derived interview questions, complete assessments, and track personal improvement.

The platform should continuously support admin-led updates as interview data and market requirements change, without requiring developers to manually rewrite the application or its content taxonomy.

Build this as a scalable, secure, maintainable educational product—not a collection of disconnected AI features.

---

**Execution Expectations**

- Do not over-document or spend excessive time planning. Build incrementally.
- Keep the application runnable throughout development.
- Test each milestone before moving to the next.
- Clearly report what has been completed, what remains, and any blockers.
- Never claim a feature is implemented unless it actually works.
- Do not leave placeholder buttons or non-functional features.
- Do not compromise backend functionality, data integrity, or security for frontend appearance.
- Do not generate all learning content immediately. Start with the approved initial domains and subtopics.
- Wait for explicit admin approval before expanding the curriculum.
- Ask questions only when essential information is missing. Make reasonable assumptions otherwise.
- When interview-source URLs and credentials are provided later, integrate them through secure configuration rather than waiting for them to build the rest of the platform.
- **Interactive and engaging frontend:** Build a modern, visually appealing, highly interactive frontend that attracts Gen Z students. The experience should feel intuitive, dynamic, and engaging rather than like a traditional learning management system. Use interactive visualizations, smooth animations, engaging progress indicators, responsive layouts, and hands-on learning experiences. Maintain a clean, professional design without sacrificing usability, accessibility, performance, or consistency.

Think of this as building a real NxtWave product that can eventually serve thousands of AI/ML students preparing for placements.
