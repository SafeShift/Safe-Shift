What can you build using Gen AI in 24 hours?
This hackathon is about speed, skill, and proving what's possible when AI agents act autonomously — not just respond. You have 24 hours to go from idea to a deployed, working agent that uses persistent memory, multi-step reasoning, and live tools to solve a real problem.

To be eligible for prizes, your submission must:

Be a fully functional autonomous agent built with OpenClaw, Hermes Agent, or something else.
For those building in cloud, use NVIDIA Nemotron models via build.nvidia.com/models.
Demonstrate live tool use and independent action — no prototypes, no demos, no slides.
What can you win?
Exclusive NVIDIA Swag
NemoClaw Track: NVIDIA Jetson
Spark track: Asus Ascent GX10
Cloud track: NVIDIA Brev GPU Credits

Getting Started
Check Your Equipment: Ensure your laptop is fully charged, and you're connected to the event's Wi-Fi

WiFi: Details will be shared onsite.

For those using Spark, here are the models pre-installed on the Spark:

Qwen 3.6 is great for the main model (use it as the primary starter model), amazing for coding tasks and also doing long tail tasks like doing research on a topic.
Gemme 4 is a well-rounded one, and speaks more precisely. So a great backup and also may work better for simple debugging and coding. It is more concise and talk less. However, there seems to sometimes be issues with tool callings so may have early stops.
Nemotron-3-Nano-Omi is not designed for OpenClaw tool calling use cases, but instead an amazing subagent to perform specific tasks and also works on VLMs. Think about a situation where you want the agent to get information about a scene? Or documents, etc…
We highly encourage leveraging these, but please feel free to use your own where you see fit!

NIM Logo
Get your endpoint for Nemotron Models
Brev Logo
Get a GPU instance
build.nvidia.com/models?q=nemotron	Brev credits
Access free serverless APIs to build enterprise generative AI apps now via build.nvidia.com. Reminder you will need to use NVIDIA Nemotron to qualify for a prize.	NVIDIA Brev is an AI and machine learning (ML) platform that empowers developers with on-demand GPU access in the cloud. You could use your Brev credits when your project goes beyond basic API calls and you need to modify, train, or build a bespoke model. Use Brev if you require the high-performance compute and increased control to develop a unique solution.
Be sure to join our Discord discord.com/invite/nvidiadeveloper and find us in the #hackathon channel

Important Reminders
•
You have 24 hours to build and deploy a working autonomous AI agent. Focus on creating something real: an agent that takes action—using persistent memory, multi-step reasoning, and live tools—without relying on hand-holding or static responses. Solve one meaningful problem cleanly and demonstrate true autonomy.
•
Showcase Agent Autonomy: Your agent must act independently—triggering APIs, processing live data, and adapting over time. Avoid complex data pipelines or external dependencies; the goal is to highlight the agent’s intelligence through action, not just output.
•
Build with NVIDIA Endpoints: To ensure fast deployment and eligibility for prizes, use Nemotron models via NVIDIA’s model endpoints at build.nvidia.com/models . Access to these endpoints is required for all submissions.
This is not a pitch. Not a prototype. Not a slideshow.

It’s a live, running agent.

Make it work.

•
Must use Nemotron model/s to win: Focus on NVIDIA Nemotron family models (e.g., nvidia-nemotron-nano-9b-v2 and llama-3_3-nemotron-super-49b-v1_5. To access the endpoint, click on the view code button at the top right corner.

🏆 Best Use of NVIDIA Nemotron
What is Nemotron Best For?
NVIDIA Nemotron models are purpose-built for agentic AI — the next generation of intelligent systems that don't just answer questions, but reason, plan, and take action. Unlike general-purpose LLMs, Nemotron excels at:

Advanced reasoning and multi-step problem-solving
Function calling to interact with external tools and APIs
Autonomous decision-making within agent workflows
Retrieval-augmented generation (RAG) for knowledge-based tasks
Multi-agent orchestration where specialized agents work together together
Think beyond chatbots → Build agents that coordinate tasks, use tools intelligently, and adapt to complex scenarios.

🎯 Ideal Projects for This Track
Winning projects will showcase true agentic behavior:

Multi-Agent Systems
Build teams of specialized AI agents (like the Report Generator: Research Agent → Outline Agent → Writer Agent → Editor)

Agentic RAG
Systems that intelligently decide WHEN to retrieve information, not just HOW (perfect for domain-specific assistants)

ReAct Pattern Workflows
Agents that Reason → Act → Observe in loops to solve problems iteratively (like automated debugging or technical support)

Tool-Calling Applications
Leverage Nemotron's exceptional ability to use external APIs and tools (finance analysis, DevOps automation, content creation)

Multi-Modal Agents
Combine Nemotron reasoning with VLMs (visual analysis + logical decision-making)

Agent Simulation & Evaluation
Use Nemotron to generate realistic test scenarios and evaluation pipelines

🚀 Get Started
Essential Resources:
Quick Start Workshops (self-paced, deploy in minutes):

Report Generator Agent Tutorial : Learn agent architecture with LangGraph
Agentic RAG Tutorial : Build smart retrieval systems
Access Nemotron:
Via OpenRouter API (fastest start)
On Hugging Face (open weights)
Model: nvidia/nvidia-nemotron-nano-9b-v2
Tools & Frameworks:
LangGraph for agent orchestration
NVIDIA NIM for inference
Tavily for web search capabilities
Learn from Past Winners: Agent examples here
Route Optimization Agent (NVIDIA NeMo Hackathon): Multi-agent system coordinating logistics with specialized agents for constraint extraction and route planning
Automated Bug Fixer (Dust Hackathon): Non-technical users describe bugs, agent autonomously diagnoses and fixes code
Multi-Agent Research System (lablab.ai): Orchestrated deep research with autonomous agent collaboration
Nemotron Model Suggestions
These powerful and efficient models are perfect for your hackathon project. We encourage you to be among the first to build with our newest suggestions:

🆕 Nemotron-super-120b-a12b
Nemotron-3-nano-30b-a3b
💡 What Judges Are Looking For
Your project should demonstrate:

✅
Autonomous reasoning: not just responding to prompts
✅
Multi-step workflows: agents that plan and execute complex tasks
✅
Tool integration: using external APIs/services intelligently
✅
Real-world applicability: solving actual problems
✅
Nemotron-specific strengths: why Nemotron is the right choice
Pro tip: Show the agent's decision-making process in your demo — let judges see it thinking, planning, and acting!

📚 Additional Resources
Developer Forums: Nemotron channel on Discord
Technical Blogs: developer.nvidia.com/nemotron
Full Workshop Repos: Available on GitHub (linked in tutorials)
DLI Course: "Building Agentic AI Applications with LLMs" for deeper learning
Remember: The best Nemotron projects build AGENTS that reason and act — not just chatbots that respond. Think orchestration, tool-use, and autonomous problem-solving! 🎉

🏆 Best Use of NVIDIA NemoClaw
What is NemoClaw Best For?
NemoClaw is an open source reference stack that simplifies running OpenClaw safely. It bundles OpenClaw with NVIDIA OpenShell, a secure runtime that enforces policy-based controls over what the agent can access: files, network, and system resources.

Unlike running OpenClaw directly, NemoClaw adds guardrails without reducing capability. It lets you deploy autonomous agents with confidence, whether on a local workstation, a DGX Spark, or in the cloud.

NemoClaw is designed for:

Secure agent deployment with minimal configuration
Policy-controlled access to files, networks, and tools
Local inference with Nemotron models, isolated from the host system
Safe experimentation: no risk to your machine or data
Production-ready workflows where security and autonomy both matter
Think beyond raw access → Build agents that act, but only within boundaries you define.

🎯 Ideal Projects for This Track
Winning projects will show how NemoClaw enables safe, powerful automation:

Secure Multi-Agent Systems
Run teams of agents, each in its own sandbox, to handle different tasks like research, writing, and execution without cross-contamination.

Policy-Driven Automation
Use NemoClaw's YAML policies to restrict agents, such as "Can access ~/Documents but not ~/Passwords" or "Can reach only trusted APIs."

Agent Sandboxing in Practice
Show how NemoClaw blocks dangerous actions like file deletion, shell execution, or outbound connections while still allowing useful tool use.

Cloud + Local Hybrid Workflows
Run the agent in Brev for testing, then deploy the same NemoClaw bundle on a DGX Spark for production.

Audit-Ready Agent Behavior
Log and review every action the agent takes, including file access, network calls, and tool usage captured by OpenShell.

Agent Lifecycle Management
Use NemoClaw to deploy, update, and monitor agents across multiple machines with the same secure configuration.

🚀 Get Started
Essential Resources:
Quick Start Guides (self-paced, deploy in minutes):

Install OpenClaw on DGX Spark or OEM GB10
Install NemoClaw on DGX Spark or OEM GB10
Try OpenClaw on Brev (cloud)
Try NemoClaw on Brev (cloud)
Access NemoClaw:
Run locally: curl -fsSL https://nvidia.com/nemoclaw.sh | bash
Run in cloud: Use Brev Launchable with nvidia/nemotron-3-super-120b-a12b
Tools & Frameworks:
OpenShell (policy engine)
OpenClaw (agent framework)
Nemotron models (reasoning core)
Brev (cloud deployment)
Learn from Past Examples:
Agent that reads financial reports and emails summaries, all inside a sandbox.
Research agent that fetches papers, writes summaries, and saves to a folder with network access restricted to trusted domains.
Daily task agent that checks calendar, sends reminders, and updates a todo list with no access to personal files unless allowed.
NemoClaw Model Suggestions
Use Nemotron models with NemoClaw for best performance and security:

nvidia/nemotron-3-super-120b-a12b
nvidia/nemotron-3-nano-30b-a3b
These models are optimized for reasoning and tool use, and work fully inside NemoClaw's sandbox.

💡 What Judges Are Looking For
Your project should demonstrate:

✅
Security by design: show how NemoClaw's policies prevent unsafe actions.
✅
Autonomous action within bounds: the agent does real work, but only what it's allowed to do.
✅
Clear policy configuration: show the YAML rules that control access.
✅
Real-world use case: solves a problem, not just a demo.
✅
NemoClaw-specific value: why did you need NemoClaw? Why not just OpenClaw?
Pro tip: Record your agent's actions. Show judges the policy logs, including how it was blocked from accessing a file or allowed to call an API. This proves the guardrails work.

📚 Additional Resources
NemoClaw GitHub: github.com/NVIDIA/NemoClaw
OpenShell Documentation: github.com/NVIDIA/OpenShell
Brev Launchables: brev.nvidia.com
Discord Community: discord.gg/nvidia-claw
Developer Portal: developer.nvidia.com/nemotron
Remember: NemoClaw isn't about locking down agents. It's about giving you control so you can build powerful agents without fear. Use it to make your work safe. Use it to make your ideas real.

AI Tools for a Quick Start
Autonomous AI agent runtimes: Hermes Agent, OpenClaw, OpenShell

Type	Description
Low Code / No Code tools	Vercel V0, Replit AI, Lovable, Codev, Bolt
AI Code Assistants	Windsurf, Cursor, GitHub Copilot, Tabnine, Qodo, Factory AI
Orchestration / App Framework	CrewAI, LangChain, LlamaIndex, Dify.ai, Haystack
Serverless API Endpoints	NVIDIA NIM, Nemotron Models, Together AI, Replicate, Cohere, Hugging Face, Fireworks AI, Open Router
Databases	Supabase, Weaviate, Pinecone
Deployment	Vercel, Replit, Supabase

Show and Tell
At 6:00 PM on Saturday, there will be a pencils down moment where you need to submit your project into this form: Submit Your Project. Judges will also be going around and you will have 3 minutes to present to them. We are limited on time so please be prepared when the judge arrives. If you are not ready, you will be disqualified.

After all demos, the NVIDIA Team will create a list of the top 5 team finalists. Those finalists will be called to the front to give a 3-minute presentation on what they built. Winners will be chosen based on these final presentations.

Judging Criteria
Your project will be evaluated based on the following criteria based on a score from 1-5:

Criteria	Description
Creativity	The project's originality and innovative problem-solving approach in addressing a challenge.
Functionality	The project's functional prototype, live demonstration effectiveness, and stability, ensuring meaningful integration of tech stack.
Scope of Completion	The project's completeness, polish, and user experience, ensuring a seamless and well-structured workflow.
Presentation	Clear, engaging, and well-structured presentation that effectively communicates the project's core use case, technical depth, and business impact to diverse audiences.
Use of NVIDIA Tools	The team's effective, impactful, and innovative integration of NVIDIA NIMs, SDKs, libraries and tools to enhance their project.
Use of NVIDIA Nemotron Models	The team's effective, impactful, and innovative integration of NVIDIA Nemotron models to enable sophisticated reasoning and agentic capabilities within their project.

Developer Resources
Accelerated Computing Hub
The Accelerated Computing Hub is an open-source repository for CUDA educational materials. We are filling it with CUDA C++ and Python tutorials, user guides, and examples to help you take your GPU accelerated code to the next level. Give us a star and keep coming back as we continue to update frequently.

NVIDIA/accelerated-computing-hub
NVIDIA Developer Program
Access technical resources, tools, and support to build with NVIDIA technologies. The NVIDIA Developer Program provides documentation, SDKs, and community forums for developers working with AI, graphics, HPC, and more.

developer.nvidia.com
NVIDIA Inception Program
NVIDIA Inception is a program designed to help startups accelerate technical innovation and business growth at all stages. Inception is free and supports members of its global community with valuable benefits from NVIDIA and partners.

nvidia.com/en-us/startups
NVIDIA Ventures
NVentures, NVIDIA's venture capital arm, invests in innovative startups that are accelerating transformation across computing, healthcare, manufacturing, automotive, and other industries.

nventures.ai
Job Opportunities at NVIDIA
Working at NVIDIA, you'll solve some of the world's hardest problems and discover never-before-seen ways to improve the quality of life for people everywhere. From healthcare to robots, self-driving cars to blockbuster movies, you'll experience it all. Plus, there's a growing list of new opportunities every single day. Explore all of our open roles, including internships and new college graduate positions.

Learn more about our current job openings, as well as university jobs.

Explore Here
Nemotron Models Ideas Portal
Customer Feedback. Add a new product idea or vote on an existing idea using the customer feedback form.

nemotron.ideas.nvidia.com
