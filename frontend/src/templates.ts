export interface ProjectTemplate {
  id: string;
  icon: string;
  name: string;
  domain: string;
  description: string;
  vision: string;
  current_state: string;
  target_goals: string;
  suggestion: {
    orchestrators: { name: string }[];
    squads: { name: string; agents: string[] }[];
    agents: { name: string; type: string; model: string; description: string }[];
  };
  /**
   * A single concrete "best case" use-case scenario for this template.
   * Generated scaffolds display this (title + narrative + payload) when
   * run.sh runs, then send `payload` to the squad as its input.
   */
  scenario: {
    title: string;
    narrative: string;
    payload: Record<string, unknown>;
  };
}

export const PROJECT_TEMPLATES: ProjectTemplate[] = [
  {
    id: 'automotive',
    icon: '🚗',
    name: 'Automotive Dealership AI',
    domain: 'automotive',
    description:
      'A luxury automotive dealership wants AI-driven inventory management across new, CPO, and trade-in vehicles — with aging prediction, showroom optimisation, and dynamic pricing recommendations.',
    vision:
      'Fully autonomous inventory management — vehicles priced, placed, and moved without manual intervention. Zero aging vehicles. Maximum margin on every lot.',
    current_state:
      'Manual pricing reviews take days. Aging vehicles are discovered too late. Showroom placement is based on gut feel. Pricing decisions are inconsistent across locations.',
    target_goals:
      'Reduce vehicle aging by 60%. Improve margin per unit by 15%. Automate 80% of pricing decisions. Optimise showroom placement in real-time.',
    suggestion: {
      orchestrators: [
        { name: 'InventoryOrchestrator' },
        { name: 'PricingOrchestrator' },
      ],
      squads: [
        { name: 'InventorySquad', agents: ['AgingPredictionAgent', 'ShowroomOptimiserAgent'] },
        { name: 'PricingSquad',   agents: ['MarketPricingAgent', 'PriceValidationAgent'] },
      ],
      agents: [
        { name: 'AgingPredictionAgent',  type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Predicts vehicle aging risk using sales velocity and market data' },
        { name: 'ShowroomOptimiserAgent', type: 'BaseAgent',             model: 'general',   description: 'Recommends showroom placement based on foot traffic and margin' },
        { name: 'MarketPricingAgent',     type: 'K9CriticActorAgent',    model: 'reasoning', description: 'Generates and critiques pricing recommendations against market comps' },
        { name: 'PriceValidationAgent',  type: 'BaseAgent',             model: 'general',   description: 'Validates final price against OEM guidelines and margin floors' },
      ],
    },
    scenario: {
      title: 'Aging Vehicle Review — 2023 BMW X5 (75 days on lot)',
      narrative:
        'A 2023 BMW X5 xDrive40i has been on the lot for 75 days — past the dealership\'s ' +
        '45-day aging threshold. The squad assesses aging risk, recommends a showroom ' +
        'placement, and drafts — then critiques and validates — a price adjustment.',
      payload: {
        event_type: 'inventory_aging_check',
        query: 'Assess this vehicle for aging risk, recommend a showroom placement, and propose a validated price adjustment.',
        vehicle: {
          vin: '5UXCR6C0XP9N12345',
          make: 'BMW',
          model: 'X5 xDrive40i',
          year: 2023,
          trim: 'Premium Package',
          days_on_lot: 75,
          list_price: 68500,
          msrp: 71200,
          mileage: 4200,
          comparable_avg_price: 66800,
          lot_location: 'Indoor Showroom Bay 3',
          recent_views: 12,
          recent_test_drives: 1,
        },
      },
    },
  },
  {
    id: 'document-intelligence',
    icon: '📄',
    name: 'Document Intelligence',
    domain: 'document-processing',
    description:
      'An enterprise document processing system that ingests contracts, invoices, and reports — extracting structured data, validating against business rules, and routing to downstream systems.',
    vision:
      'Zero-touch document processing — contracts, invoices, and reports extracted, validated, and routed automatically with no human intervention for standard documents.',
    current_state:
      'Manual data entry from PDFs. Business rule validation is ad-hoc. Routing decisions depend on staff availability. Error rates are high on unstructured documents.',
    target_goals:
      'Achieve 95% touchless processing. Reduce extraction errors to <1%. Cut processing time from days to minutes.',
    suggestion: {
      orchestrators: [
        { name: 'ExtractionOrchestrator' },
        { name: 'ValidationOrchestrator' },
      ],
      squads: [
        { name: 'ExtractionSquad',  agents: ['DocumentClassifierAgent', 'DataExtractorAgent'] },
        { name: 'ValidationSquad',  agents: ['BusinessRuleAgent', 'ComplianceCheckerAgent'] },
      ],
      agents: [
        { name: 'DocumentClassifierAgent', type: 'BaseAgent',             model: 'general',   description: 'Classifies document type — contract, invoice, report, or claim' },
        { name: 'DataExtractorAgent',      type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Extracts structured fields with iterative self-correction' },
        { name: 'BusinessRuleAgent',       type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Validates extracted data against configurable business rules' },
        { name: 'ComplianceCheckerAgent',  type: 'K9CriticActorAgent',    model: 'reasoning', description: 'Critiques and refines compliance flags before escalation' },
      ],
    },
    scenario: {
      title: 'Inbound Invoice — Acme Industrial Supplies (INV-20458)',
      narrative:
        'A scanned invoice arrives from a vendor. The squad classifies the document type, ' +
        'extracts structured fields (vendor, line items, totals, PO reference), checks it ' +
        'against business rules, and runs a compliance check before routing to AP.',
      payload: {
        event_type: 'document_received',
        query: 'Classify this document, extract structured fields, validate against business rules, and check compliance before routing to AP.',
        document_text:
          'INVOICE #INV-20458\n' +
          'Vendor: Acme Industrial Supplies Ltd.\n' +
          'Bill To: Northwind Manufacturing\n' +
          'Date: 2026-05-30   Due: 2026-06-29\n' +
          'Line Items:\n' +
          '  1. Stainless Steel Brackets (x500) ... $4,250.00\n' +
          '  2. Hex Bolts M8 (x2000) ............... $1,180.00\n' +
          '  3. Freight & Handling .................. $310.00\n' +
          'Subtotal: $5,740.00\n' +
          'Tax (8.25%): $473.55\n' +
          'Total Due: $6,213.55\n' +
          'Payment Terms: Net 30\n' +
          'PO Reference: PO-88291',
      },
    },
  },
  {
    id: 'customer-service',
    icon: '💬',
    name: 'Customer Service AI',
    domain: 'customer-service',
    description:
      'An intelligent customer service platform that triages inbound requests, resolves common queries autonomously, escalates complex issues, and ensures quality through critique-actor evaluation.',
    vision:
      'Instant, empathetic resolution for every customer inquiry — 24/7, at scale, with consistent quality regardless of channel or time of day.',
    current_state:
      'Long wait times. Inconsistent responses across agents. High volume of repeat contacts. Staff burnout on routine queries eating into capacity for complex issues.',
    target_goals:
      'Resolve 70% of inquiries autonomously. Reduce average handle time by 40%. Improve CSAT score to >4.5/5. Free agents to focus on high-value interactions.',
    suggestion: {
      orchestrators: [
        { name: 'TriageOrchestrator' },
        { name: 'ResolutionOrchestrator' },
      ],
      squads: [
        { name: 'TriageSquad',     agents: ['IntentClassifierAgent', 'SentimentAgent'] },
        { name: 'ResolutionSquad', agents: ['KnowledgeBaseAgent', 'ResponseQualityAgent'] },
      ],
      agents: [
        { name: 'IntentClassifierAgent', type: 'BaseAgent',          model: 'general',   description: 'Classifies customer intent — billing, support, complaint, or enquiry' },
        { name: 'SentimentAgent',        type: 'BaseAgent',          model: 'general',   description: 'Detects customer sentiment and urgency level' },
        { name: 'KnowledgeBaseAgent',    type: 'BaseAgent',          model: 'general',   description: 'Retrieves and synthesises answers from the knowledge base' },
        { name: 'ResponseQualityAgent',  type: 'K9CriticActorAgent', model: 'reasoning', description: 'Generates response, critiques tone and accuracy, refines before sending' },
      ],
    },
    scenario: {
      title: 'Inbound Support Email — Duplicate Billing Charge',
      narrative:
        'A premium customer emails support reporting they were charged twice for their ' +
        'monthly subscription. The squad classifies intent and sentiment, retrieves the ' +
        'refund policy, then drafts — critiques — and refines a reply before it is sent.',
      payload: {
        event_type: 'customer_message',
        query:
          "I've been charged twice for my subscription this month — $49.99 showed up on " +
          "my card on the 3rd AND the 5th. I've been a loyal customer for 3 years and this " +
          'is really frustrating. Can someone fix this today?',
        channel: 'email',
        customer_id: 'CUST-88213',
        account_tier: 'Premium',
      },
    },
  },
  {
    id: 'financial-analysis',
    icon: '📊',
    name: 'Financial Analysis AI',
    domain: 'finance',
    description:
      'A financial analysis platform that ingests market data and portfolio positions, generates risk assessments, validates regulatory compliance, and produces investment recommendations.',
    vision:
      'Real-time portfolio risk intelligence — anomalies detected, compliance verified, and investment narratives generated before markets open.',
    current_state:
      'Risk reports generated overnight. Anomaly detection is manual and reactive. Compliance review is a bottleneck. Narrative writing consumes analyst hours per report.',
    target_goals:
      'Reduce risk reporting cycle from overnight to 15 minutes. Detect anomalies in real-time. Automate 80% of compliance report generation.',
    suggestion: {
      orchestrators: [
        { name: 'RiskOrchestrator' },
        { name: 'ReportingOrchestrator' },
      ],
      squads: [
        { name: 'RiskSquad',      agents: ['MarketDataAgent', 'RiskScoringAgent', 'AnomalyDetectorAgent'] },
        { name: 'ReportingSquad', agents: ['NarrativeAgent', 'ComplianceReportAgent'] },
      ],
      agents: [
        { name: 'MarketDataAgent',       type: 'BaseAgent',             model: 'general',   description: 'Fetches and normalises market data from configured sources' },
        { name: 'RiskScoringAgent',      type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Iteratively scores portfolio risk with self-validation' },
        { name: 'AnomalyDetectorAgent',  type: 'BaseAgent',             model: 'reasoning', description: 'Detects statistical anomalies in position data' },
        { name: 'NarrativeAgent',        type: 'K9CriticActorAgent',    model: 'reasoning', description: 'Drafts investment narrative, critiques for bias, refines output' },
        { name: 'ComplianceReportAgent', type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Validates report against regulatory requirements iteratively' },
      ],
    },
    scenario: {
      title: 'Overnight Risk Run — Portfolio PF-10231',
      narrative:
        'Overnight market data shows NVDA dropped 6.8% and now represents 18.4% of ' +
        'portfolio PF-10231 — above the 15% single-name concentration limit. The squad ' +
        'pulls market data, scores portfolio risk, flags the concentration anomaly, ' +
        'drafts an investment narrative, and validates the compliance report.',
      payload: {
        event_type: 'portfolio_risk_check',
        query: 'Assess overnight risk for this portfolio, flag anomalies, and produce a compliance-ready risk narrative.',
        portfolio_id: 'PF-10231',
        portfolio_value: 18750000,
        var_95_1d: 312000,
        concentration_limit_pct: 15,
        positions: [
          { ticker: 'NVDA', shares: 4200, weight_pct: 18.4, change_1d_pct: -6.8 },
          { ticker: 'TLT', shares: 9000, weight_pct: 9.1, change_1d_pct: 1.2 },
          { ticker: 'XOM', shares: 5400, weight_pct: 7.5, change_1d_pct: 0.4 },
        ],
      },
    },
  },
  {
    id: 'saving-grace',
    icon: '🎸',
    name: 'Saving Grace — Plant',
    domain: 'Music',
    description:
      'Robert Plant wants to use AI for his new Saving Grace team — covering tour logistics, travel, concert production, band operations, equipment, finance, and fan engagement. Reaching for higher rock.',
    vision:
      'Full operational intelligence for Saving Grace — every aspect of the touring machine automated so the band focuses entirely on the music.',
    current_state:
      'Tour logistics managed manually across promoters and travel agents. Concert production ad-hoc. Equipment tracked on spreadsheets. Managers historically swindle money — no financial transparency. Fan engagement fragmented. Band welfare and maintenance reactive.',
    target_goals:
      'Reaching for Higher Rock — powered by K9X. 50% reduction in tour planning overhead. Full financial transparency — zero unexplained manager deductions. Real-time concert production coordination. Automated equipment and band maintenance. Unified fan engagement. Every show better than the last.',
    suggestion: {
      orchestrators: [
        { name: 'TourOrchestrator' },
        { name: 'CreativeOrchestrator' },
        { name: 'BandOrchestrator' },
        { name: 'FinanceOrchestrator' },
      ],
      squads: [
        { name: 'TourLogisticsSquad', agents: ['VenueBookingAgent', 'TravelAgent', 'SchedulingAgent', 'ConcertProductionAgent'] },
        { name: 'CreativeSquad',      agents: ['SetlistCurationAgent', 'FanEngagementAgent', 'PerformanceAnalyticsAgent'] },
        { name: 'BandOpsSquad',       agents: ['EquipmentAgent', 'CrewManagementAgent', 'BandMaintenanceAgent', 'SoundEngineerAgent'] },
        { name: 'FinanceSquad',       agents: ['BudgetAgent', 'TicketingAgent', 'MerchandiseAgent', 'ContractAuditAgent'] },
      ],
      agents: [
        { name: 'VenueBookingAgent',      type: 'BaseAgent',             model: 'general',   description: 'Books and negotiates venues across the tour route' },
        { name: 'TravelAgent',            type: 'BaseAgent',             model: 'general',   description: 'Coordinates flights, hotels, and ground transport for band and crew' },
        { name: 'SchedulingAgent',        type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Iteratively optimises tour schedule across venues, travel windows, and band availability' },
        { name: 'ConcertProductionAgent', type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Coordinates stage design, lighting, sound setup, and production logistics per show' },
        { name: 'SetlistCurationAgent',   type: 'K9CriticActorAgent',    model: 'reasoning', description: 'Drafts setlist based on regional audience data, critiques flow and crowd energy, refines' },
        { name: 'FanEngagementAgent',     type: 'BaseAgent',             model: 'general',   description: 'Unifies fan communication across Instagram, YouTube, and email channels' },
        { name: 'PerformanceAnalyticsAgent', type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Analyses per-show data — track resonance, crowd response, and regional patterns' },
        { name: 'EquipmentAgent',         type: 'BaseAgent',             model: 'general',   description: 'Tracks all instruments and equipment — inventory, transport, condition, and insurance' },
        { name: 'CrewManagementAgent',    type: 'BaseAgent',             model: 'general',   description: 'Manages crew scheduling, roles, and availability across the tour' },
        { name: 'BandMaintenanceAgent',   type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Monitors band welfare — rest schedules, health flags, travel fatigue, and performance readiness' },
        { name: 'SoundEngineerAgent',     type: 'K9CriticActorAgent',    model: 'reasoning', description: 'Generates sound configuration per venue, critiques acoustics, refines mix recommendations' },
        { name: 'BudgetAgent',            type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Tracks tour budget — actuals vs forecast, variance alerts, and manager expense auditing' },
        { name: 'TicketingAgent',         type: 'BaseAgent',             model: 'general',   description: 'Manages ticket pricing, availability, and dynamic pricing per venue' },
        { name: 'MerchandiseAgent',       type: 'BaseAgent',             model: 'general',   description: 'Forecasts and manages merchandise inventory and revenue per show' },
        { name: 'ContractAuditAgent',     type: 'K9CriticActorAgent',    model: 'reasoning', description: 'Audits promoter and manager contracts for hidden deductions, swindles, and unfair terms — flags anomalies before signing' },
      ],
    },
    scenario: {
      title: 'Tour Stop — The Roundhouse, London (2026-06-20)',
      narrative:
        "Tonight's show at The Roundhouse is nearly sold out (3,050 / 3,200). The squad " +
        'coordinates logistics for the day and the ContractAuditAgent reviews the promoter ' +
        "settlement — including a suspicious £9,750 'production miscellaneous' " +
        'deduction — before it is signed off.',
      payload: {
        event_type: 'tour_day_ops',
        query: "Coordinate logistics for tonight's show and review the promoter settlement for irregularities before sign-off.",
        show: {
          venue: 'The Roundhouse, London',
          date: '2026-06-20',
          load_in: '12:00',
          soundcheck: '16:30',
          doors: '19:00',
          set_time: '21:00',
          capacity: 3200,
          tickets_sold: 3050,
        },
        promoter_settlement: {
          gross_ticket_revenue_gbp: 137250,
          promoter_fee_pct: 15,
          merchandise_cut_pct: 20,
          deductions: [
            { label: 'Venue rental', amount_gbp: 18000 },
            { label: 'Security', amount_gbp: 4200 },
            { label: 'Production miscellaneous', amount_gbp: 9750 },
          ],
        },
      },
    },
  },
  {
    id: 'god-almighty',
    icon: '✦',
    name: 'God the Almighty',
    domain: 'Divinity',
    description:
      'The Almighty is overwhelmed. 8 billion humans are simultaneously submitting requests for world peace, lottery wins, revenge on their ex, and help finding car keys. A cosmic AI system is urgently required to triage the infinite request queue, audit karma, verify humanitarian merit, and ensure desires — sports cars, perfect abs, that promotion — are permanently deprioritized.',
    vision:
      'Infinite compassion, finite miracles — a perfectly fair, infinitely scalable divine request management system that processes 8 billion simultaneous prayers with cosmic patience and zero bias.',
    current_state:
      '8 billion humans submitting requests simultaneously. No triage. No karma verification. Lottery requests flooding the queue. System overwhelmed since approximately 3000 BC.',
    target_goals:
      'Process all legitimate requests within geological timeframes. Eliminate lottery and revenge requests entirely. Maintain cosmic fairness score above 99.9%. Lottery requests route to /dev/null.',
    suggestion: {
      orchestrators: [
        { name: 'RequestTriageOrchestrator' },
        { name: 'KarmaOrchestrator' },
        { name: 'HumanitarianOrchestrator' },
        { name: 'DesireManagementOrchestrator' },
        { name: 'MiracleOrchestrator' },
      ],
      squads: [
        { name: 'RequestTriageSquad',     agents: ['RequestClassifierAgent', 'WhiningFilterAgent', 'RepeatOffenderAgent', 'UrgencyRankingAgent'] },
        { name: 'KarmaAuditSquad',        agents: ['GoodDeedsCounterAgent', 'SelflessnessCheckAgent', 'CommunityServiceAgent', 'KarmaScoreAgent'] },
        { name: 'HumanitarianSquad',      agents: ['HumanitarianCheckAgent', 'AltruismScoreAgent', 'GlobalImpactAgent'] },
        { name: 'DesireManagementSquad',  agents: ['DesireDeprioritizationAgent', 'LotteryRequestAgent', 'MaterialDesireAgent', 'RevengeRequestAgent'] },
        { name: 'MiracleAllocationSquad', agents: ['MiracleBudgetAgent', 'HumilityVerificationAgent', 'WorthinessCriticAgent', 'DivinePatienceAgent'] },
      ],
      agents: [
        { name: 'RequestClassifierAgent',      type: 'BaseAgent',             model: 'general',   description: 'Classifies request: genuine need, humanitarian, desire, lottery, or "help me find my keys". Last two skip the queue — into /dev/null.' },
        { name: 'WhiningFilterAgent',          type: 'BaseAgent',             model: 'general',   description: 'Detects duplicate requests submitted more than 3 times in a week. Applies exponential backoff. No exceptions.' },
        { name: 'RepeatOffenderAgent',         type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Tracks lifetime request history. Flags chronic complainants for mandatory 30-day cooling-off period.' },
        { name: 'UrgencyRankingAgent',         type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Iteratively ranks urgency across 8 billion concurrent requests. Described internally as the hardest job in the universe.' },
        { name: 'GoodDeedsCounterAgent',       type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Audits lifetime good deeds with full iterative validation. Karma score is final.' },
        { name: 'SelflessnessCheckAgent',      type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Determines if the good deed was genuinely selfless or just performed for social media. Instagram posts reduce score by 40%.' },
        { name: 'CommunityServiceAgent',       type: 'BaseAgent',             model: 'general',   description: 'Verifies community service hours. Court-ordered hours do not count.' },
        { name: 'KarmaScoreAgent',             type: 'BaseAgent',             model: 'reasoning', description: 'Computes final karma score. Needs > 500 for basic requests. Miracles require > 9999.' },
        { name: 'HumanitarianCheckAgent',      type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Verifies whether the request has any humanitarian merit whatsoever.' },
        { name: 'AltruismScoreAgent',          type: 'BaseAgent',             model: 'reasoning', description: 'Measures true altruism. The system knows.' },
        { name: 'GlobalImpactAgent',           type: 'BaseAgent',             model: 'reasoning', description: 'Measures whether granting this request makes the world even 0.01% better. Lottery wins consistently score 0.00.' },
        { name: 'DesireDeprioritizationAgent', type: 'BaseAgent',             model: 'general',   description: 'Moves all desires to the bottom of the eternal queue. ETA: undefined.' },
        { name: 'LotteryRequestAgent',         type: 'BaseAgent',             model: 'general',   description: 'Handles all lottery requests. Routing destination: /dev/null. Response time: never.' },
        { name: 'MaterialDesireAgent',         type: 'BaseAgent',             model: 'general',   description: 'Processes requests for material possessions. Deprioritized below world peace and someone\'s lost umbrella.' },
        { name: 'RevengeRequestAgent',         type: 'BaseAgent',             model: 'general',   description: 'All revenge requests flagged and denied. Requester karma reduced by 200 for submitting.' },
        { name: 'MiracleBudgetAgent',          type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Manages the strictly limited miracle budget. 3 miracles per century per continent. Frequently overspent.' },
        { name: 'HumilityVerificationAgent',   type: 'BaseAgent',             model: 'general',   description: 'Verifies the requester demonstrated basic humility. Entitlement detected = immediate rejection.' },
        { name: 'WorthinessCriticAgent',       type: 'K9CriticActorAgent',    model: 'reasoning', description: 'Generates divine ruling, critiques for fairness across all 8 billion complainants, refines until defensible in cosmic court.' },
        { name: 'DivinePatienceAgent',         type: 'BaseAgent',             model: 'general',   description: 'Checks if sufficient time has elapsed since last answered request. Minimum wait: 7 years. No appeals.' },
      ],
    },
    scenario: {
      title: 'Incoming Prayer Batch — 3 Requests',
      narrative:
        'Three prayers arrive simultaneously: a world-peace request from a habitual ' +
        "do-gooder, a 47th lottery request from a repeat offender who Instagrams their " +
        "good deeds, and a first-time 'help me find my keys' request. The squad " +
        'classifies, audits karma, checks humanitarian merit, and issues a final ruling.',
      payload: {
        event_type: 'prayer_request_batch',
        query: 'Triage these incoming requests, audit requester karma, assess humanitarian merit, and rule on miracle allocation.',
        requests: [
          {
            id: 'REQ-0001',
            text: "Please let world peace happen, I'll do anything.",
            requester_karma_history: '200 hrs community service, donates blood quarterly',
          },
          {
            id: 'REQ-0002',
            text: 'I need to win the lottery, I deserve it more than anyone.',
            requester_karma_history: 'Submitted 47 times this week, posts good deeds to Instagram immediately after doing them',
          },
          {
            id: 'REQ-0003',
            text: "Can you help me find my car keys, I'm late for work.",
            requester_karma_history: 'First request ever, generally kind person',
          },
        ],
      },
    },
  },
  {
    id: 'healthcare',
    icon: '🏥',
    name: 'Healthcare AI Assistant',
    domain: 'healthcare',
    description:
      'A clinical AI assistant that processes patient intake data, suggests triage priorities, cross-references medical guidelines, and generates care plan summaries for review by clinicians.',
    vision:
      'Every patient receives the right care at the right time — clinical decisions supported by AI, guidelines always current, care plans generated in seconds not hours.',
    current_state:
      'Clinicians spend hours on documentation. Triage decisions vary by staff experience. Clinical guidelines are rarely consulted in real-time. Care plan writing is manual and inconsistent.',
    target_goals:
      'Reduce documentation time by 50%. Standardise triage accuracy to >95%. Generate care plan summaries in under 60 seconds. Free clinicians for patient-facing time.',
    suggestion: {
      orchestrators: [
        { name: 'TriageOrchestrator' },
        { name: 'ClinicalOrchestrator' },
      ],
      squads: [
        { name: 'IntakeSquad',   agents: ['SymptomExtractorAgent', 'UrgencyClassifierAgent'] },
        { name: 'ClinicalSquad', agents: ['GuidelineCheckerAgent', 'CarePlanAgent'] },
      ],
      agents: [
        { name: 'SymptomExtractorAgent',  type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Extracts and validates symptom data from unstructured intake notes' },
        { name: 'UrgencyClassifierAgent', type: 'BaseAgent',             model: 'general',   description: 'Classifies patient urgency — critical, urgent, routine' },
        { name: 'GuidelineCheckerAgent',  type: 'K9ValidationLoopAgent', model: 'reasoning', description: 'Cross-references symptoms against clinical guidelines iteratively' },
        { name: 'CarePlanAgent',          type: 'K9CriticActorAgent',    model: 'reasoning', description: 'Drafts care plan summary, critiques for clinical accuracy, refines' },
      ],
    },
    scenario: {
      title: 'Patient Intake — 58F, Chest Tightness + Hypertension',
      narrative:
        'A 58-year-old patient with controlled hypertension and type 2 diabetes reports ' +
        'two days of exertional chest tightness, including one episode radiating to the ' +
        'left arm. The squad extracts structured symptom data, classifies urgency, ' +
        'cross-references cardiac guidelines, and drafts a care plan summary for review.',
      payload: {
        event_type: 'patient_intake',
        query: 'Extract symptoms, classify urgency, check against clinical guidelines, and draft a care plan summary for clinician review.',
        patient_id: 'PT-44210',
        intake_note:
          'Patient: 58F. Presents with intermittent chest tightness over past 2 days, ' +
          'worse on exertion, mild shortness of breath. History of hypertension ' +
          '(controlled, lisinopril 10mg) and type 2 diabetes (metformin 500mg BID). ' +
          'No prior cardiac events. BP 148/92, HR 88, SpO2 97%. Denies nausea, denies ' +
          'radiating pain currently but reports one episode radiating to left arm ' +
          'yesterday evening lasting ~10 minutes, resolved with rest.',
      },
    },
  },
];
