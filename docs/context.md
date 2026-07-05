# RupeeRadar — Project Context

## Overview
RupeeRadar is an **AI-powered personal finance assistant** that helps working
professionals understand where their money goes by analyzing their bank
statement data. Users upload raw bank statements; the app cleans and
categorizes transactions, detects recurring payments, computes financial
metrics, and presents insights through a dashboard/report.

> Source of truth: [problemStatement.txt](problemStatement.txt)

## Problem Being Solved
Working professionals make hundreds of monthly transactions across UPI, cards,
bank transfers, subscriptions, EMIs, rent, shopping, food delivery, travel, and
investments. Bank statements contain all this data but are hard to understand
because transaction descriptions are **messy, inconsistent, and hard to
categorize manually**.

## Key Questions the Product Must Answer
- What are my biggest spending categories?
- How much did I spend this month?
- Which transactions are recurring subscriptions or EMIs?
- What was my biggest transaction?
- What are the top insights from my spending behavior?

## Core Requirements (end-to-end pipeline)
1. **Ingest** — Accept bank statement data as input.
2. **Extract / Clean** — Parse messy data into a structured transaction format.
3. **Categorize** — Group transactions into: Food, Travel, Shopping, Bills,
   EMI, Subscriptions, Salary, Rent, Investments, Other.
4. **Detect recurring** — Identify subscriptions, EMIs, rent, SIPs, insurance.
5. **Compute metrics** — Total income, total spend, savings, top categories,
   biggest transactions.
6. **Generate insights** — Clear, human-readable insights using actual amounts.
7. **Present** — Simple UI / dashboard / downloadable report.

## Expected Deliverable (working prototype must demonstrate)
- Cleaned transaction data
- Categorized expenses
- Recurring payment detection
- Spend summary dashboard
- **At least three** personalized financial insights
- A final shareable report / visual summary
- Deployed or locally runnable application

## Evaluation Criteria
- Accuracy of transaction cleaning and categorization
- Quality of financial insights
- Ability to handle **real-world messy** transaction descriptions
- Simplicity and usefulness of the UX
- Completeness of the end-to-end workflow
- **Privacy-conscious** handling of sensitive financial data

## Constraints & Guidance
- **Prioritize a working end-to-end prototype** over perfect support for every
  bank format.
- Technology stack and implementation approach are open/free choice.
- Handle sensitive financial data in a privacy-conscious way.

## Suggested Categories (canonical list)
`Food` · `Travel` · `Shopping` · `Bills` · `EMI` · `Subscriptions` · `Salary` ·
`Rent` · `Investments` · `Other`

## Current Project State
- Repo contents so far: `docs/problemStatement.txt` (the challenge brief),
  this `context.md`, and `architecture.md`.
- No application code, stack, or tooling chosen yet — greenfield.

## Open Decisions (to resolve when implementation starts)
- Input format(s) to support first (CSV export, PDF statement, XLSX?).
- Tech stack (frontend, backend, data/AI layer).
- Categorization approach (rules/regex, ML model, or LLM-based classification).
- Recurring-detection method (periodicity + merchant matching heuristics).
- Where processing happens (local vs. cloud) given privacy requirements.
- Report/export format (in-app dashboard, PDF, shareable link).

> Proposed resolutions for these decisions are detailed in
> [architecture.md](architecture.md).
