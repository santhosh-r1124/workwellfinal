export interface MetricBaseline {
  metric: string;
  baseline: number;
  current: number;
  deviation: number;
  median: number;
  mean: number;
  std: number;
  mad: number;
  rolling_avg: number;
  trend: number;
  window_days: number;
}

export interface BaselineResponse {
  employee_id: string;
  metrics: Record<string, MetricBaseline>;
}

export interface PatternSignal {
  name: string;
  change: number;
  anomalous_days: number;
}

export interface PatternRecord {
  date: string;
  state: string;
  confidence: number;
  duration_days: number;
  signals: PatternSignal[];
}

export interface DataSourceInfo {
  key: string;
  label: string;
  category: string;
  what: string;
  why: string;
  where: string;
  retention: string;
  who_can_access: string;
  default_enabled: boolean;
  collectible: boolean;
  enabled: boolean;
}

export interface ChatSource {
  title: string;
  url?: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}
