# Why Not Reinforcement Learning for AI-TDP

**Document type:** Architecture decision record (ADR-style technical report)  
**Project:** AI-TDP — Hierarchical / behavioral cyber-physical analysis → IDS rule generation for ICS  
**Primary dataset in scope:** SWaT.A12 (Ensign Pre-UAT, 11 Mar 2026)  
**Status:** Decision recommendation — **do not use Reinforcement Learning (RL) as the primary learning method**  
**Audience:** Project leads, ML engineers, ICS security stakeholders  
**Related:** Root [`README.md`](../../README.md), hourly generalization outputs under `baselines/outputs/hourly_generalization/`

---

## 1. Executive summary

AI-TDP’s product goal is **not** to maximize a game score. It is to:

1. Learn **normal cyber-physical behavior** of an ICS from traffic and process features.  
2. Detect **anomalous behavior** at runtime with **few false blocks**.  
3. Propose **enforceable IDS rules** (IP/port, CIP tag writes, payload/signatures, etc.).  
4. Install rules only after **human approval** (initially), with **revocation** and optional TTL.  
5. **Retrain offline** only on traffic confirmed as normal.

Under that design, **Reinforcement Learning is a poor primary fit**.

RL assumes an agent that repeatedly acts in an environment, receives a **reward**, and optimizes long-horizon return. In this project:

- There is **no safe, dense, automatic reward** for “correct block vs allow” on live ICS.  
- Wrong actions can become **IDS block rules** that disrupt a plant.  
- Available data is essentially **one labeled-by-period day** of SWaT, not millions of interactive episodes.  
- Stakeholders explicitly chose **human-gated rules**, **offline learning on normal only**, and **precision over recall**.

**Recommendation:** Keep **unsupervised / self-supervised behavior learning + conservative anomaly scoring + human-approved rule generation + offline normal corpus expansion**. Treat RL, if ever, as a **narrow optional policy layer** long after the detect→propose→approve loop is stable—not as the behavior learner.

---

## 2. Locked product context (why this report exists)

### 2.1 End-to-end vision

```text
ICS traffic / process windows
        │
        ▼
Behavior ML (what “normal” looks like)
        │
        ▼
Anomaly score + explainable evidence
        │
        ▼
Rule proposer → candidate IDS rules
        │
        ▼
Human approve / edit / reject  (early deployment)
        │
   ┌────┴────┐
   ▼         ▼
IDS enforce   Reject / revoke → confirmed normal corpus
(TTL / revocable)              │
                               ▼
                     Offline retrain on normal only
```

### 2.2 Stakeholder decisions already made

| Decision | Choice | Implication for RL |
| :--- | :--- | :--- |
| Rule authority | Human approval in the beginning | The “action” that matters is not auto-executed by an RL agent |
| False alarm handling | Rule revocation | Feedback is sparse, delayed, and human-mediated |
| Rule lifetime | Lifetime **or** revocable (TTL allowed) | Policy must be auditable, not a black-box Q-table of blocks |
| Rule content | IP/port, CIP tag write, payload, signature, … | Need **explainable** proposals, not opaque action indices |
| Model update | Offline on normal traffic only | Contradicts classic online RL that learns from every step |
| Error preference | Prefer **fewer false blocks** | High cost of false positives; RL needs that cost in the reward |

### 2.3 Empirical warning from current experiments

Hourly Behavior Generalization (`baselines/outputs/hourly_generalization/`) trained the stacked cascade on one clock hour and scored the next hour of the **same** regime. All four experiments were judged **behavioral_drift**, with **~89–100%** of evaluation windows above a train-hour 95th-percentile Mahalanobis threshold—including **normal→normal** pairs.

Interpretation for the product:

- Even mild **phase change within one day** already looks “anomalous” to a static behavior envelope.  
- Day-to-day legitimate drift would be worse under a static model.  
- The fix is **better normality coverage + conservative rule gating + human-confirmed normal expansion**—not an RL agent that learns to block more aggressively from sparse rewards.

---

## 3. What “using RL” would actually mean here

People often say “RL” when they mean any adaptive system. For this report, RL means the standard MDP framing:

| RL element | In a game / robot | In AI-TDP IDS rule generation |
| :--- | :--- | :--- |
| **State** \(s\) | Screen / joint angles | Window of net/proto/phys features, plant mode, open rules |
| **Action** \(a\) | Move / shoot | Allow, alert, propose rule \(r\), install rule, revoke, retrain, … |
| **Transition** | Simulator physics | Real ICS + operators + IDS (partially observed, irreversible side effects) |
| **Reward** \(R\) | Score / distance | Must encode safety, false blocks, missed attacks, operator load |
| **Episode** | Game round | Hours/days of plant operation |
| **Goal** | Maximize return | Minimize unsafe blocks while catching attacks—under human governance |

Possible RL formulations people might propose:

1. **RL as behavior learner** — agent learns “normal” by maximizing some reconstruction / curiosity reward.  
2. **RL as detector calibrator** — agent tunes thresholds online.  
3. **RL as rule installer** — agent chooses when to push block rules to the IDS.  
4. **RL as continual adapter** — agent decides when to update the model on new traffic.

This report argues that **(1) is the wrong paradigm**, **(3) conflicts with human approval and precision-first policy**, and **(2)/(4) are either unnecessary or better solved with non-RL methods** (gated offline updates, dynamic thresholds, multi-normal banks).

---

## 4. Core reasons RL is not appropriate

### 4.1 There is no safe automatic reward on a live ICS

RL lives or dies by the reward function.

For AI-TDP, a correct reward would need to know, online:

- Was this window **benign new normal** or **attack**?  
- Did a block prevent damage—or did it **cause** process upset?  
- Was a human reject a true false positive or operator mistake?

On SWaT.A12 in this repo:

- There is **no per-row attack label** in the multilayer CSV.  
- Labels are **coarse periods** (morning normal / afternoon attack window).  
- There is **no per-attack schedule** in-repo for reward shaping.

So any online RL reward is either:

- **Proxy-based** (reconstruction error, rarity) → collapses to unsupervised AD with extra instability, or  
- **Human-based** (approve/reject) → sparse, delayed, expensive—and then the system is really **human-in-the-loop supervised feedback**, not classic RL that needs dense interaction.

**Verdict:** You do not have the reward channel RL requires for safe primary learning.

---

### 4.2 Wrong actions become permanent (or semi-permanent) plant controls

In Atari, a bad action loses points. In AI-TDP, a bad action can become:

```text
anomaly → proposed rule → (if auto) IDS block → valve/pump command path disrupted
```

Even with human approval, an RL agent trained to “maximize detections” will tend to:

- Propose **many** rules to harvest reward, or  
- Learn brittle policies that overfit one day’s afternoon patterns.

Stakeholders already chose:

- Prefer **fewer false blocks**.  
- Human approval early.  
- Revocation when wrong.

That is a **conservative governance loop**, not an explore/exploit controller. Exploration (trying risky blocks “to learn”) is ethically and operationally unacceptable on ICS.

**Verdict:** RL’s exploration requirement fights ICS safety and the project’s precision preference.

---

### 4.3 Offline-on-normal contradicts online RL

The locked learning policy is:

> Retrain **offline**, only on **confirmed normal** traffic.

Classic RL (and most online continual RL) updates from the stream of experience, including ambiguous and attack periods. If the agent adapts through the afternoon attack window without a perfect gate, it will **absorb attack behavior into “normal”** or into a policy that no longer flags it.

Safety-gated continual adaptation can exist **without RL** (replay buffers, EWC, multi-normal banks, human reject→normal corpus). Those methods match the product loop. End-to-end RL does not.

**Verdict:** The chosen update policy is **batch / offline / curated**—orthogonal to primary RL.

---

### 4.4 Data volume and interaction budget are far too small

Effective deep RL typically needs:

- A **simulator** or cheap resettable environment, and/or  
- **Large** numbers of interactions.

What AI-TDP has today:

- One SWaT day (~8 hours @ 1 Hz → 28,860 seconds).  
- Phase 3 windows on the order of **thousands**, not millions.  
- No high-fidelity interactive SWaT simulator wired into a gym-style loop in this repo.  
- No second plant / multi-day corpus for policy transfer.

Training an RL policy to install CIP/IP block rules from this footprint is underdetermined and will overfit noise and hour-specific modes (already visible in hourly drift experiments).

**Verdict:** The data regime favors **representation learning + statistical detection**, not RL.

---

### 4.5 Credit assignment is hostile to rule generation

IDS rules are:

- Discrete, symbolic, auditable (5-tuple, CIP tag, payload pattern).  
- Sparse in time (one rule may cover many future flows).  
- Evaluated minutes to days later (process impact, operator revoke).

RL credit assignment over delayed, symbolic, human-edited actions is notoriously hard. Meanwhile, the product needs:

- **Attribution** (“this CIP write tag + source IP looked abnormal”), then  
- A **deterministic rule proposer**.

That is closer to **anomaly explanation + template mapping** than to learning a neural policy over rule strings.

**Verdict:** Rule generation wants **interpretability and templates**, not opaque policy gradients.

---

### 4.6 Non-stationarity is real—but RL is not the only (or best) answer

ICS traffic **does** change hour to hour and day to day. That is why static Mahalanobis envelopes fail.

Better-aligned methods for this exact problem family (behavior drift / “new normal”):

| Approach | Role | Fits AI-TDP decisions? |
| :--- | :--- | :--- |
| Multi-normal / prototype bank | Many legitimate modes | Yes — reduces false blocks on phase change |
| Experience replay + offline retrain | Expand normal corpus after human reject/revoke | Yes — matches offline-on-normal |
| Safety-gated continual AD | Update only on high-confidence normals | Yes — if gated by human/policy, not free RL |
| Dynamic / precision-first thresholds | Stop fixed 95% cut from traveling badly | Yes — fewer false blocks |
| Test-time adaptation (carefully gated) | Mild shift without full retrain | Conditional — never unattended on attack periods |
| Deep RL policy for blocks | Learn allow/block from reward | **No** as primary method |

Literature on CPS/ICS anomaly detection under drift increasingly emphasizes **gated adaptation, incremental/meta updates on normal data, and dynamic thresholds**—not RL as the plant behavior model. Fixed thresholds under distribution shift are a documented failure mode on SWaT-like settings; the remedy is calibration and adaptive normality, not an RL blocker.

**Verdict:** Continual / adaptive **normality management** ≠ Reinforcement Learning.

---

### 4.7 Human-in-the-loop already supplies the “policy”

With human approval:

```text
Agent proposes → Human decides → IDS executes
```

The human **is** the policy for high-impact actions. Turning that into RL means either:

- Learning to imitate the human (then **imitation learning / supervised** on approve-reject logs is enough), or  
- Learning to bypass/optimize around the human (unacceptable early, and conflicts with “approval in the beginning”).

Approve/reject/revoke logs are gold for:

- Supervised calibration of score thresholds,  
- Ranking which rule templates humans accept,  
- Expanding the normal corpus.

They are a weak, expensive signal for online RL.

**Verdict:** HITL feedback → **supervised / offline calibration**, not primary RL.

---

### 4.8 Objective mismatch: behavior learning vs reward maximization

Root project science (see repository `README.md`):

> Learn how the system **normally behaves** across network, protocol, and physical domains.  
> Attack detection is **downstream** of behavior embeddings.

RL optimizes **returns for actions**. Behavior learning optimizes **representations of normal trajectories** (reconstruction, prediction residual, density, etc.).

Conflating them produces systems that:

- Chase reward proxies,  
- Drift when the proxy correlates with load/phase instead of attack,  
- Fail to emit **behavior explanations** suitable for IDS rules.

**Verdict:** Primary objective is **behavioral representation**, not RL return.

---

### 4.9 Compliance, audit, and explainability

ICS security controls must be:

- Reviewable by engineers,  
- Reversible (revocation),  
- Tied to observable traffic features.

An RL policy (DQN/PPO/etc.) that maps embeddings → block decisions is hard to certify. A pipeline that says:

> “Score exceeded precision-oriented threshold; top evidence = `writes_HMI_MV101` from `IP_x`; proposed rule = deny CIP Write Tag MV101 from IP_x for 24h; awaiting human approval”

is auditable.

**Verdict:** RL policies fight the audit needs of IDS rule generation.

---

## 5. Failure modes if RL were forced into AI-TDP

| Failure mode | What happens | Product impact |
| :--- | :--- | :--- |
| **Reward hacking** | Agent maximizes “anomalies caught” via over-flagging | Flood of rules; false blocks; operator rejects everything |
| **Poisoned normality** | Online updates treat slow attacks as new normal | Silent loss of detection |
| **Exploration damage** | Agent tries novel block actions to learn | Process disruption |
| **Sparse reward collapse** | Only rare human labels | Unstable training; random policies |
| **Sim-to-real gap** | Policy trained on one SWaT day | Breaks next day / next mode (already seen hourly) |
| **Non-explainable actions** | Neural action head | Cannot map to CIP/IP/signature rules cleanly |
| **Cascade + RL compound fragility** | Unstable latents + unstable policy | Worse than either alone |

The hourly generalization results are an early warning: **even without RL**, normality is brittle. Adding RL on top amplifies operational risk.

---

## 6. Clarifying related ideas that are *not* primary RL

These are often confused with “we need RL”:

| Idea | Actually is | Use in AI-TDP? |
| :--- | :--- | :--- |
| Continual learning with replay | Incremental offline/online AD | **Yes** — after human-confirmed normal |
| Dynamic thresholds | Statistical calibration | **Yes** — precision-first |
| Multi-armed bandit for threshold | Lightweight online calibration | Optional later, not core |
| Imitation learning from operator approve/reject | Supervised policy clone | Optional once HITL logs exist |
| RL for alert triage ranking | Narrow decision aid | Optional Phase 3+ product polish |
| Deep RL to learn plant physics / blocks | Full MDP control of IDS | **No** |

**Optional future (narrow) RL:** only after shadow mode + assisted approval are stable, and only for **low-risk decisions** (e.g., ordering which *already-proposed* rules a human sees first)—never for unsupervised installation of plant blocks, and never as the behavior encoder.

---

## 7. What to use instead (aligned stack)

### 7.1 Learning

- Unsupervised / self-supervised **behavior models** on confirmed-normal windows (reconstruction, forecasting residual, density on embeddings).  
- Prefer **explainable scoring** (feature attributions, per-domain residuals) over opaque cascade latents alone.  
- Maintain a **multi-normal bank** (modes/days) so legitimate phase/day change does not equal “attack.”

### 7.2 Detection policy

- **Precision-first** thresholds validated on held-out normal periods.  
- Ambiguous scores → **alert only**, no rule proposal.  
- High-confidence + rule-mappable evidence → **propose** IDS rule.

### 7.3 Governance (already chosen)

- Human approval initially.  
- Revocable / TTL rules.  
- Reject and revoke expand **normal corpus**.  
- Offline retrain only on that corpus.

### 7.4 Adaptation to day-to-day change

```text
New day looks different
  → may raise scores
  → few high-precision proposals (not a flood)
  → human rejects benign drift
  → windows added to normal corpus
  → offline retrain
  → fewer proposals next week
```

**Who tells the model the new traffic is normal?**  
Humans (reject/revoke) and curated offline normal sets—not an RL reward hack.

---

## 8. Decision statement

| Question | Answer |
| :--- | :--- |
| Should RL be the primary method to learn ICS behavior for AI-TDP? | **No** |
| Should RL install IDS rules autonomously? | **No** |
| Should RL replace human approval early? | **No** |
| Should the project pursue continual / adaptive normality? | **Yes** (non-RL) |
| Might RL appear later as a narrow assistive policy? | **Only optionally**, low-risk, after HITL metrics are strong |

**Architecture decision:**  
**Reject Reinforcement Learning as the core of AI-TDP.**  
Adopt **behavior learning + precision-oriented anomaly detection + explainable rule proposal + human-gated enforcement + offline normal retraining**.

---

## 9. One-page briefing (for stakeholders)

**Why not RL?**

1. We cannot safely define an automatic reward on a live plant.  
2. Wrong actions become IDS blocks—exploration is unacceptable.  
3. We already decided: human approval, revocation, offline train on normal only, fewer false blocks.  
4. We have one SWaT day of data—not an RL interaction budget.  
5. We need auditable rules (IP/CIP/signature), not opaque policies.  
6. Day-to-day drift is real; fix it with **confirmed multi-normal learning**, not RL.  
7. Current experiments already show normal→normal false alarming; RL would not remove that root cause.

**What we do instead:** learn behavior → detect conservatively → propose rules → humans decide → retrain offline on true normal.

---

## 10. References (selected, problem-aligned)

Project-internal:

- `README.md` — behavior-learning objective; dual pipelines; locked splits.  
- `baselines/outputs/hourly_generalization/hourly_generalization_report.md` — normal-hour drift / false-alarm evidence.  
- Product decisions captured in project discussions (human approval, revocation, offline-on-normal, precision-first, rich rule types).

External themes supporting non-RL adaptation for CPS/ICS AD:

- Safety-gated / drift-aware continual anomaly detection for cyber-physical systems (update only in high-confidence regions).  
- Incremental / meta-learning AD for evolving CPS with dynamic thresholds (e.g., SWaT/WADI-oriented incremental AD).  
- “New normal” / test-time adaptation for unsupervised time-series AD (distribution shift of normality).  
- Evidence that **fixed thresholds** fail under score distribution shift on SWaT-like reconstruction detectors.  
- Continual AD benchmarks showing **simple experience replay** often competitive with heavier continual methods.  
- ICS continual learning studies favoring **EWC + replay** over naive sequential fine-tuning (when adaptation is required).

These lines of work motivate **gated continual normality management**, not deep RL as the IDS rule brain.

---

## 11. Document control

| Field | Value |
| :--- | :--- |
| Title | Why Not Reinforcement Learning for AI-TDP |
| Path | `reports/docs/WHY_NOT_REINFORCEMENT_LEARNING.md` |
| Recommendation | **Do not use RL as primary method** |
| Revisit when | Multi-day normal corpora exist; HITL approve/reject logs are large; shadow-mode false-block rate is proven tiny—and only for optional low-risk assistive policies |
