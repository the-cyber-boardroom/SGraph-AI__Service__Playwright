---
title: SG/Edge — commercial angles & business model implications
date: 2026-05-20
status: strategy / business case
audience: founders, commercial leads, investors, prospective enterprise customers
scope: how the technical architecture creates new product surfaces and pricing levers
related:
  - sg-edge__01-solution-overview.md
  - sg-edge__02-edge-fleet.md
  - sg-edge__03-targets.md
---

# Why this document exists

The SG/Edge architecture was built to solve a technical problem (LE rate limits, TLS at scale, ephemeral compute). But the *way* it solves that problem — DNS-driven routing, scale-to-zero per-edge isolation, vendor-neutral primitives, encrypted payloads end-to-end — happens to be very close to the shape of what enterprise and security-conscious customers will pay premium prices for.

This document is the inventory: what billable units the architecture creates, what business models it enables, and which customer segments find each property valuable. None of these are speculative — they are direct consequences of architectural choices already documented in the other three docs.

# The core insight — architecture as a pricing surface

Most SaaS platforms have one or two dimensions to price on: seats, storage, requests, compute hours. SG/Edge creates a much wider surface because each architectural choice maps to a property that some customer segment will pay a premium for:

```
+------------------------------------------------------------------+
|  Architectural choice            |  Becomes a billable property  |
+------------------------------------------------------------------+
|  Per-edge isolation              |  Dedicated tenancy            |
|  (one CF distribution per        |  ($0.50/mo cost,              |
|   customer / environment)        |   premium price)              |
|                                                                  |
|  Component portability           |  Sovereignty / data           |
|  (CF -> any CDN; Route 53 ->     |  residency packages           |
|   any DNS; EC2 -> any VM)        |                               |
|                                                                  |
|  Scale-to-zero economics         |  "Hibernation tier" for       |
|                                  |  inactive customers           |
|                                                                  |
|  Coexistence with traditional    |  Tier ladder: ephemeral ->    |
|  always-on path                  |  always-on -> dedicated       |
|                                                                  |
|  Per-target backend choice       |  Compute SKU mix              |
|  (EC2 / Fargate / shared)        |                               |
|                                                                  |
|  Encrypted payloads + log        |  Zero-knowledge certification |
|  metadata stripping              |  add-on                       |
|                                                                  |
|  Multi-region / multi-cloud      |  Resilience / BCP tier         |
|  capable                         |                               |
+------------------------------------------------------------------+
```

The unifying theme: most of these properties are *expensive to provide as add-ons* in conventional SaaS architectures (rebuild for isolation, rewrite for portability, re-architect for sovereignty). In SG/Edge they're already there, latent — every customer's deployment can be configured into any of these shapes without code changes.

# Customer segments and what they buy

Five distinct customer segments emerge naturally from the property matrix:

```
+------------------+---------------------------+----------------------+
|  Segment         |  Buys                     |  Property leveraged  |
+------------------+---------------------------+----------------------+
|  SMB / startup   |  Cheap, fast, just works  |  Scale-to-zero       |
|                  |                           |  economics           |
|                  |                           |                      |
|  Enterprise IT   |  Predictable cost,        |  Coexistence with    |
|                  |  always-on, vendor SLA    |  traditional always- |
|                  |                           |  on path             |
|                  |                           |                      |
|  Security-       |  Verifiable isolation,    |  Per-edge isolation, |
|  conscious       |  audit trail, zero-       |  encrypted payloads, |
|  (legal, finance,|  knowledge                 |  centralised        |
|   healthcare)    |                           |  logging + redaction |
|                  |                           |                      |
|  Sovereignty-    |  Data stays in country,   |  Component           |
|  constrained     |  control of provider mix  |  portability,        |
|  (EU, UAE, KSA,  |                           |  multi-cloud         |
|   gov)           |                           |                      |
|                  |                           |                      |
|  Resilience-     |  BCP plan with proof of   |  Multi-region,       |
|  required        |  cross-provider failover  |  multi-cloud,        |
|  (financial      |                           |  vendor-neutral      |
|   services,                                                          |
|   critical infra)                                                    |
+------------------+---------------------------+----------------------+
```

The same codebase serves all five. Configuration determines which mode a given customer's deployment is in.

# Five business models the architecture enables

## 1. Tiered ephemerality — pay for what's on

Traditional SaaS prices on "you exist" (seats, storage). SG/Edge can price on "you're using it":

```
+--------------------------------------------------------------------+
|  Tier              |  What's on                |  Price model      |
+--------------------------------------------------------------------+
|  Hibernation       |  CF + DNS only            |  ~$1/mo / edge    |
|                    |  (proxy + vault at zero)  |  fixed            |
|                    |                                                |
|  Office hours      |  Proxy fleet on M-F       |  ~$15/mo + usage  |
|                    |  business hours;          |                   |
|                    |  scales to zero overnight |                   |
|                    |                                                |
|  Always-warm       |  N>=1 proxy, vault wakes  |  Usage + small    |
|                    |  on access                |  fixed             |
|                    |                                                |
|  Dedicated         |  Pre-warmed, own CF       |  Premium fixed    |
|                    |  distribution, own ALB    |  + low usage      |
|                    |  option, SLA              |                   |
+--------------------------------------------------------------------+
```

This is genuinely new pricing surface. A long-tail customer with a few hours of activity per week pays a couple of dollars; an enterprise customer with steady traffic pays for steady traffic; a security-sensitive customer pays for premium isolation. The customer self-selects the tier.

Notable: a customer at Hibernation tier costs us almost nothing to keep ($0.50/mo Route 53 zone + a few hundred CF requests/month). We can keep ex-customers and trial customers in Hibernation indefinitely without a margin problem. This is unusual; most SaaS has fixed per-customer cost.

## 2. Per-environment pricing — sell isolation as a product

Today, "give me a dev environment" usually means "yes, you have one, share it with everyone else." SG/Edge makes per-customer dev/QA/staging environments cheap enough to sell as discrete units:

```
+-----------------------------------------------------------------+
|  Product:  Customer Environments                                |
+-----------------------------------------------------------------+
|                                                                 |
|  prod        |  one dedicated edge              |   $X / mo     |
|  staging     |  one dedicated edge              |   $X / mo     |
|  qa          |  one dedicated edge              |   $X / mo     |
|  dev         |  one dedicated edge              |   $X / mo     |
|  preview/PR  |  ephemeral edges per PR          |   pay-per-use |
|                                                                 |
|  Each is a separate CF distribution, separate wildcard cert,    |
|  separate DNS zone, separate proxy fleet, separate targets.     |
|  Zero shared state between environments.                        |
|                                                                 |
+-----------------------------------------------------------------+
```

The infrastructure cost per environment is ~$0.50/mo + usage. The premium price is for the property the customer buys (isolation, named separateness, ability to point auditors at it as a distinct deployment).

This is selling architecture as a product. "Your dev and prod are physically separate AWS resources, with separate IAM, separate certs, separate everything" is a thing some customers will pay for. It's also a thing that's straightforwardly true with this architecture.

## 3. Sovereignty packages — pricing data residency

Component portability creates real sovereignty optionality:

```
+--------------------------------------------------------------------+
|  Package           |  Where things run                              |
+--------------------------------------------------------------------+
|  Standard          |  AWS eu-west-1 (or any AWS region)             |
|                                                                     |
|  EU-only           |  All compute, DNS, edge in EU regions          |
|                    |  Audit trail showing no data leaves EU         |
|                                                                     |
|  EU-only +         |  Above, but DNS on Cloudflare EU,              |
|  CDN-diverse       |  CDN not on US-headquartered provider          |
|                                                                     |
|  Customer-managed  |  Customer brings their own cloud account;      |
|  hosting           |  we deploy SG/Edge into it; we operate it      |
|                                                                     |
|  Sovereign         |  Customer's data centre / sovereign cloud;     |
|  on-prem           |  full air-gap option                           |
+--------------------------------------------------------------------+
```

For EU customers wary of US CLOUD Act exposure, "everything runs on Cloudflare DNS + Hetzner compute + LE certs, no US-headquartered provider in the data path" is a real and defensible posture. For Middle Eastern / Asian customers wary of any cross-border data movement, deploying into their cloud account or sovereign cloud is feasible because the architecture has no AWS-specific data plane (only convenience couplings — Route 53, CloudFront — that have clean replacements).

The commercial implication: each step up the sovereignty ladder is a price tier. The customer pays for the operational cost of running in a less-convenient environment (Hetzner is cheap to run on but harder to operate at small scale; sovereign cloud is more expensive and slower to deploy) plus a margin for the assurance.

## 4. Resilience / BCP — selling vendor-neutral failover

Most SaaS BCP stories are "we have multi-AZ deployments." SG/Edge can credibly offer:

```
+--------------------------------------------------------------------+
|  BCP tier          |  Failover scope                               |
+--------------------------------------------------------------------+
|  Standard          |  Multi-AZ within one AWS region               |
|                    |  (what most SaaS offers)                      |
|                                                                     |
|  Multi-region      |  Active-passive across regions                |
|                                                                     |
|  Multi-cloud       |  Standby on different cloud provider          |
|                    |  (proxy fleet on Hetzner, can take over       |
|                    |   if AWS region down — DNS-level failover)    |
|                                                                     |
|  Multi-provider    |  Active-active across cloud providers         |
|                                                                     |
|  Datacenter-       |  Active-active across datacenters owned by    |
|  diverse           |  different operators                          |
+--------------------------------------------------------------------+
```

This isn't aspirational. The architecture's edge tier is OpenResty on commodity VMs; the registry is DNS; the wakers are stateless functions. Standing up an OpenResty fleet on Hetzner that can take over if AWS goes down is a real operational project, but a tractable one — the codebase already works there.

For customers in regulated industries (financial services, critical infrastructure, anything subject to operational resilience requirements like DORA in the EU), being able to point to a working cross-cloud failover is a material differentiator. "We have a documented, tested failover to a non-AWS provider that can be activated in under N minutes" is a sentence very few SaaS competitors can write truthfully.

The commercial implication: BCP tiers are recurring premium revenue, and the property compounds with sovereignty packages.

## 5. Embedded / OEM — customer-hosted SG/Edge

The architecture supports a "we ship you the platform; you run it" model that traditional multi-tenant SaaS struggles with:

```
+--------------------------------------------------------------------+
|  Model                |  Who hosts                                  |
+--------------------------------------------------------------------+
|  Standard SaaS        |  We do                                      |
|                                                                      |
|  Bring-your-own-cloud |  Customer's AWS / GCP / Azure account;      |
|                       |  we operate it under contract               |
|                                                                      |
|  Embedded / OEM       |  Customer's data centre or product;         |
|                       |  customer operates it; we license + support |
|                                                                      |
|  White-label edge     |  Customer's brand on top; their customers   |
|                       |  consume it as if customer-built            |
+--------------------------------------------------------------------+
```

Because SG/Edge is small (~$15/mo to run, low operational complexity once configured), shipping it as a deployable unit is realistic. The pricing model shifts from per-user / per-request to license + support, which is what large enterprise procurement is comfortable with.

This is particularly interesting for resellers — security vendors, MSPs, sovereign-cloud operators — who want to offer something like SG/Vault or SG/Send under their brand without the engineering investment.

# Cross-cutting commercial properties

A few properties of the architecture create commercial advantages that aren't tied to a specific business model:

## Customer acquisition cost asymptotes near zero

For self-serve / freemium / trial users, the marginal cost of acquisition is approximately the cost of one CF distribution + one Route 53 zone + a brief proxy fleet boot:

```
+----------------------------------------------------------------+
|  Acquisition cost breakdown                                    |
+----------------------------------------------------------------+
|  Trial signup:                                                 |
|    CF distribution (free until traffic)             $0.00      |
|    ACM cert (free)                                  $0.00      |
|    Route 53 zone                                    $0.50/mo   |
|    Proxy fleet boot (one-time, ~90s)                $0.01      |
|    Vault target (ephemeral, only while in use)      ~$0.05/hr  |
|                                                                |
|  Customer who tries once and never returns:                    |
|    Total ongoing cost:                              $0.50/mo   |
|    Until we manually GC them                                   |
|                                                                |
|  Customer who returns occasionally:                            |
|    Cost scales with their usage; we earn margin                |
|    even at low engagement                                      |
+----------------------------------------------------------------+
```

This means freemium tiers can be genuine — not "freemium with a hidden ceiling" — and conversion paths can be patient. The customer who tries us in March and doesn't come back until November still has their environment available; they don't have to start over.

## Per-customer cost scales with usage, not existence

In traditional SaaS, every customer carries some fixed overhead (a row in a multi-tenant database, a slot on a shared cluster, monitoring overhead). SG/Edge customers cost almost nothing when idle. Customers who use the product pay for what they use; customers who don't, don't.

The commercial implication: gross margin profile is fundamentally different from multi-tenant SaaS. The unit economics are closer to AWS itself ("you pay for what you use") than to Salesforce ("you pay for seats whether they log in or not").

## Audit / compliance story is genuinely strong

Because the architecture's properties are *real*, not marketing — encrypted payloads are encrypted, logs are redacted at source, isolation is per-CF-distribution — the audit story is verifiable rather than performative:

- SOC 2 controls: easier to evidence ("here's the Vector config that strips IPs; here's the proof it's deployed on every proxy")
- ISO 27001: separation of environments is per-AWS-resource, not per-database-row
- GDPR: client metadata stripping is at the proxy, before it reaches storage
- Zero-knowledge claims: payloads are AES-GCM encrypted in the browser before any HTTP request leaves; CF cannot decrypt them

For customers whose procurement requires these certifications and audits, the architecture itself does much of the work, reducing the documentation and process overhead substantially.

## Engineering team scales differently

Because so much of the platform is commodity (OpenResty, DNS, EC2), the engineering team needed to operate it is smaller and uses better-documented technologies than a typical SaaS stack. This is itself a commercial property — fewer hires required to scale, less key-person risk, easier to outsource specific operational functions to standard MSPs.

# Concrete pricing scenarios — illustrative

Some sketches of what specific deals could look like, to make the abstract concrete:

## Scenario A — SMB freemium

```
- Free tier: 1 vault, hibernation by default, $0/mo while idle
- Paid tier $9/mo: always-warm, 5 vaults
- Margin: positive even on free users (CF is free at trial volume)
```

## Scenario B — mid-market dev shop

```
- Customer wants per-PR preview environments
- Pricing: $X/mo base + $0.10 per preview env per day
- Each preview env is one SG/Edge edge, scale-to-zero outside business hours
- Customer pays for actual usage, no infra overhead for stale PRs
```

## Scenario C — enterprise with sovereignty needs

```
- Customer requires EU-only data residency, Cloudflare-not-AWS CDN
- Tier: Sovereignty EU + CDN-diverse
- Pricing: $Y/mo per environment + premium for sovereignty package
- Margin: higher, justified by operational cost of EU-only ops
```

## Scenario D — regulated industry with BCP requirements

```
- Customer is a fintech subject to DORA
- Requires documented cross-cloud failover, tested quarterly
- Tier: Multi-provider BCP + Sovereignty EU
- Pricing: $Z/mo per environment, BCP add-on, sovereignty add-on, quarterly DR test included
- Margin: premium; few competitors can deliver this credibly
```

## Scenario E — embedded OEM

```
- Security vendor wants to offer SG/Vault under their brand
- Model: white-label license + support
- Pricing: license fee + revenue share above threshold
- Margin: high gross margin on license; lower opex (customer operates)
```

# What this means for the roadmap

This commercial framing has implications for technical priorities:

1. **The MVP scope (in `sg-edge__01-solution-overview.md`) is correct as-is.** Phase 1 proves the riskiest mechanics; Phase 2 wires in vault targets. The commercial features build on top of this foundation.

2. **Phase 3 (production hardening) should include explicit multi-region support.** This unlocks the Resilience/BCP tier — one of the highest-margin business models.

3. **A "Phase 4 — portability hardening" is implied by the commercial framing.** Build and validate at least one non-AWS deployment (probably Hetzner + Cloudflare DNS) before the sovereignty packages can be commercially offered. This is a few weeks of work and unlocks the EU customer segment.

4. **The customer-managed hosting model needs operator tooling.** "Here's how to deploy SG/Edge into your AWS account" requires Terraform / Pulumi modules, runbooks, and a support model. Worth scoping as a separate workstream.

5. **The audit / compliance story should be productised.** The architecture properties (encrypted payloads, log redaction, per-edge isolation) deserve their own marketing page and SOC 2 / ISO 27001 evidence package. Most of the technical work is already there; the gap is presentation and process.

# Risks and where commercial framing oversells

Honest counterweights:

- **"Scale-to-zero" is true at low volumes but adds operational complexity that competitors with always-on infra don't have.** The cold-cold first-user UX is real and some segments (especially enterprise) will not tolerate it. Mitigation: those segments buy the Always-warm / Dedicated tiers, which solve this by paying more for less hibernation.

- **The sovereignty story is only as strong as the operational maturity behind it.** Selling "EU-only deployment" requires actually having the EU-only deployment running, monitored, and supportable by EU-based staff. The architecture allows this; the company needs to invest in it.

- **The BCP claims need to be tested, not just architected.** "We have cross-cloud failover" without a regular drill is a marketing claim, not a real capability. Investment required.

- **Customer-managed hosting changes the support model.** Customers who self-host will hit problems we don't see in our own environment. This needs explicit support tooling, telemetry, and contractual scope-of-support definitions.

- **Pricing tiers proliferating creates internal complexity.** Each tier needs SKUs, billing logic, customer education, sales enablement. The architecture enables many tiers; commercial discipline is needed to not offer all of them at once. Recommend launching with 2-3 tiers and expanding deliberately.

# Where this fits with the rest of the product family

SG/Edge isn't priced in isolation. It's the routing/isolation layer beneath everything else:

```
+-------------------------------------------------------+
|                  SG product family                    |
+-------------------------------------------------------+
|                                                       |
|   Consumer-facing products:                           |
|     SG/Vault    - encrypted personal vaults           |
|     SG/Send     - encrypted file delivery             |
|     SG/Tools    - utilities and CLIs                  |
|                                                       |
|   Infrastructure:                                     |
|     SG/API      - the platform API surface            |
|     SG/Edge     - routing, isolation, edge tier  <-- new |
|     sg-compute  - underlying compute primitives       |
|                                                       |
+-------------------------------------------------------+
```

SG/Edge is best understood as *how the other products are deployed*, not as a standalone product (though it can be sold standalone for embedded / OEM scenarios). Pricing tiers for SG/Edge effectively become deployment tiers for SG/Vault and SG/Send. A customer's choice between "Standard SG/Vault" and "Sovereign EU SG/Vault" is technically a choice between SG/Edge tiers.

This means SG/Edge is a force multiplier for the rest of the product line. Each new SG/Edge tier expands the addressable market for every product hosted on top of it.

# Summary

The SG/Edge architecture was built for technical reasons. By construction, it also creates commercial properties that conventional SaaS architectures struggle to offer: real isolation per environment, genuine scale-to-zero economics, credible vendor portability, verifiable zero-knowledge claims, and a path to cross-cloud resilience.

Each of these is a billable property — separately, in combination, or as the foundation of new product lines (OEM, sovereign deployments, regulated-industry packages). The same codebase serves all of them; configuration determines which tier a given customer is on.

The strategic implication: SG/Edge is less an infrastructure project and more a commercial repositioning. It turns the SG product family from "a privacy-focused SaaS" into "a privacy, sovereignty, and resilience platform that can deploy almost anywhere." That's a different conversation with enterprise procurement, with regulators, and with investors.
