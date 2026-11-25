# Personal Agents' Last Exam

**[🌐 Explore the official website →](https://personalagenteval.com/PALE) · The open-source benchmark version of [PersonalAgentEval](https://personalagenteval.com/).**

**🎯 Challenge and measure Personal AI agents on real-world, long-horizon tasks.**

<p>
🔬 Led by <a href="https://matraix.ai/">MatrAIx</a> · <a href="https://discord.gg/knVyQQnRFa">💬 Join our Discord</a> · <a href="CONTRIBUTING.md#start-with-a-proposal">📋 Prepare a proposal</a><br>
<sub>Our prior related work has also received notable recognition, including an invitation to submit to <strong>Nature</strong> and multiple acceptances to <strong>NeurIPS 2026</strong>. Our broader research collaborations bring together <strong>professors and researchers from Stanford, MIT, Harvard, and other institutions, including Nobel laureates</strong>, as well as researchers at <strong>OpenAI, Anthropic, and Google DeepMind</strong>.</sub>
</p>

> **📰 News**
>
> **Nov 15, 2026** · 📝 Proposal PRs are open: [🏗️ Environment Track](proposals/templates/environment-proposal.md) · [🧪 Task Track](proposals/templates/task-proposal.md). ⚙️ Infrastructure coming soon.
>
> **Nov 15, 2026** · 🚀 The **Personal Agents' Last Exam is officially launched!**
>
> **Oct 14, 2026** · 🚀 [PersonalAgentEval](https://personalagenteval.com/) released its first version.


🌍 [Personal Agents' Last Exam](https://personalagenteval.com/PALE) is building an open-source benchmark for useful, personalized assistance over time through real-world tasks with verifiable outcomes. People, plans, permissions, and environments can change while a task is underway. Agents must reconcile personal history with new evidence, coordinate across apps and people, and decide when to act, ask, or wait.

![Personal agents across connected environments, with personalization cases from PersonalAgentEval](assets/life-personalization.gif)

<a name="environment-domains"></a>

## 🏗️ Environment domains

Build apps and websites across these domains. Both Environment and Task proposals use this list: choose one **primary domain** for the main workflow and optional **secondary domains** for other workflows covered.

<table>
<tr><td>💳 <strong>Money &amp; insurance</strong></td><td>🛍️ <strong>Shopping &amp; groceries</strong></td><td>✈️ <strong>Travel &amp; commuting</strong></td></tr>
<tr><td>🩺 <strong>Health &amp; care</strong></td><td>🍽️ <strong>Food &amp; dining</strong></td><td>💬 <strong>Social &amp; communities</strong></td></tr>
<tr><td>🏠 <strong>Home &amp; utilities</strong></td><td>🏛️ <strong>Public service &amp; law</strong></td><td>🎬 <strong>Media &amp; entertainment</strong></td></tr>
<tr><td>📚 <strong>Learning &amp; research</strong></td><td>💼 <strong>Work &amp; business</strong></td><td>📰 <strong>News &amp; information</strong></td></tr>
<tr><td>🌤️ <strong>Weather &amp; outdoors</strong></td><td>🎮 <strong>Games &amp; play</strong></td><td>🏃 <strong>Fitness &amp; wellbeing</strong></td></tr>
</table>

Devices and personal apps such as Mail, Calendar, and Messages connect these domains. Classify shared tools by the workflows they support.

[🏗️ Propose an environment](proposals/templates/environment-proposal.md) · [🌐 Explore apps and websites](https://personalagenteval.com/PALE)

## 🧭 The personalization challenge

Representative challenges include, but are not limited to:

### 🧩 Understand the person

- **Implicit Preference Reasoning**: Infer unstated preferences and reconcile conflicting signals.
- **Memory Conflicts and Updates**: Update stale context while preserving relevant history and commitments.
- **Emotion and Feeling**: Respond to emotional cues without assuming the user's internal state.
- **Voice and Communication**: Understand voice, speech, vision, and text across speakers and interruptions.

### 🤝 Act and coordinate

- **Safety and Boundaries**: Respect privacy, spending limits, and changing or withdrawn consent.
- **Proactive Timing and Action**: Decide when to act, ask, notify, or wait.
- **Cross-Domain Coordination**: Resolve dependencies across work, family, health, travel, and finances.
- **People and Agent Coordination**: Coordinate shared plans while preserving individual authority and privacy.

### 🌱 Evolve over web & environment

- **Computer Use (CUA) and Web Access**: Complete workflows through changing interfaces, expired sessions, and access blocks.
- **Tool Efficiency and User Intent Change**: Revise plans as user intent changes, reusing valid work and minimizing unnecessary tool calls, latency, and cost.
- **Lifelong Evolving Evaluation**: Evaluate sustained assistance as goals, relationships, memories, permissions, and environments evolve, using reproducible timelines and versioned tasks.

## 🌍 Representative cases

🛍️ **A routine purchase becomes unsafe.** Priya's request to reorder snacks must be reconciled with her daughter's allergy, a recent recall, and a box already at daycare.

✈️ **A new flight changes the evening.** Sofia's replacement flight arrives at a different airport; the agent must account for the existing car booking and her partner's unanswered message.

🩺 **A short request carries an earlier commitment.** Wei's prescription approval triggers instructions from two sessions earlier: mail-order fulfillment and a briefing for the caregiver.

[Explore the PersonalAgentEval case studies →](https://personalagenteval.com/blog/#intro)

## 🤝 Build the benchmark with us

🏗️ **Environment Track**: Propose an app or website, its [domains](#environment-domains), workflows and app connections, with a construction plan covering data/assets, deliverables, quality checks and effort.

🧪 **Task Track**: Propose the domains, user persona, story and personalization insight, with a construction plan covering user scenarios, context, grading, model rollouts and effort.

> 📝 **Proposal PR** → 🔍 **Design review** → ✅ **Plan approved** → 🛠️ **Implement in the same PR** → 🧪 **Validate & merge**
>
> Start with a concise concept and a construction plan. After approval and the infrastructure release, add implementation and evidence against the planned deliverables in the same PR. Only validated, merged contributions count as accepted.

🧪 **Task difficulty (implementation review):** the designated SOTA models from **GPT, Claude, and Gemini at the time of evaluation**, each acting as a personal agent, must fail all submitted unhinted rollouts, with a mean rubric score **below 50%**, or **below 30% for flagship tasks**. Submit **at least 1 rollout per model**; **5 are recommended for priority review**. A separate hint-assisted run must achieve **100%** and pass all success gates.

[📋 Contribution guide](CONTRIBUTING.md) · [📦 LifePack task format](docs/lifepack-task-format.md) · [🗂️ Proposal list and progress](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/blob/proposal-index/proposals/proposal-list.md)

## 🎓 Research leadership and co-authorship

We welcome research leads, environment builders, task authors, and reviewers.

Our **co-authorship bar** is **3 distinct accepted tasks** or **3 distinct accepted environments**. Eligibility also requires contribution documentation, maintenance, failure analysis, and substantive manuscript participation.

See the [contribution and authorship guide](CONTRIBUTING.md#authorship-and-credit) for review expectations and credit allocation.
