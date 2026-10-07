import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Mark } from "../components/AppShell";

interface WellnessMetric {
  category: string;
  current: number;
  previous: number;
  trend: "up" | "down" | "stable";
  recommendation: string;
}

interface Insight {
  id: string;
  title: string;
  description: string;
  severity: "high" | "medium" | "low";
  affectedEmployees: number;
  recommendation: string;
  action: string;
}

const WELLNESS_METRICS: WellnessMetric[] = [
  {
    category: "Average Stress Level",
    current: 4.3,
    previous: 4.8,
    trend: "down",
    recommendation: "Stress levels improving. Maintain current wellness initiatives.",
  },
  {
    category: "Average Sleep Hours",
    current: 6.9,
    previous: 6.5,
    trend: "up",
    recommendation: "Sleep quality improving. Continue sleep hygiene programs.",
  },
  {
    category: "Work-Life Balance Score",
    current: 9.2,
    previous: 8.8,
    trend: "up",
    recommendation: "Balance is excellent. Maintain flexible work arrangements.",
  },
  {
    category: "Burnout Risk (High)",
    current: 8.3,
    previous: 11.7,
    trend: "down",
    recommendation: "Significant improvement. Target remaining at-risk employees.",
  },
  {
    category: "Mental Health Score",
    current: 9.2,
    previous: 8.9,
    trend: "up",
    recommendation: "Mental health improving. Scale successful interventions.",
  },
  {
    category: "Team Productivity",
    current: 91.8,
    previous: 88.4,
    trend: "up",
    recommendation: "Productivity gains correlate with better wellness. Continue programs.",
  },
];

const INSIGHTS: Insight[] = [
  {
    id: "1",
    title: "Night Shift Burnout Alert",
    description: "Night shift employees show 30% higher burnout risk compared to day shift.",
    severity: "high",
    affectedEmployees: 1,
    recommendation: "Implement rotation schedules and additional wellness support for night shift workers.",
    action: "Schedule wellness intervention session",
  },
  {
    id: "2",
    title: "Meeting Load Impact",
    description: "Employees with >4 hours of daily meetings show 25% lower focus time and 40% more context switches.",
    severity: "high",
    affectedEmployees: 2,
    recommendation: "Implement 'No Meeting Hours' policy and consolidate meeting schedules.",
    action: "Schedule meeting optimization workshop",
  },
  {
    id: "3",
    title: "Sleep Deficit Pattern",
    description: "Team members working >8 hours daily average only 6.2 hours of sleep.",
    severity: "medium",
    affectedEmployees: 3,
    recommendation: "Promote work-from-home options and flexible end times for overworked employees.",
    action: "Recommend flex-time arrangements",
  },
  {
    id: "4",
    title: "Positive Wellness Trend",
    description: "Overall team stress levels down 12% over the past month with improved sleep and mood.",
    severity: "low",
    affectedEmployees: 6,
    recommendation: "Document and scale the wellness programs that are working well.",
    action: "Create best practices guide",
  },
];

export default function ManagementConsultant() {
  const navigate = useNavigate();
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(INSIGHTS[0]);
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null);

  useEffect(() => {
    const role = localStorage.getItem("mgmt_role");
    if (role !== "consultant") {
      navigate("/management");
    }
  }, [navigate]);

  const getTrendIcon = (trend: string) => {
    if (trend === "up") return "📈";
    if (trend === "down") return "📉";
    return "→";
  };

  const getSeverityColor = (severity: string) => {
    if (severity === "high") return "bg-red-900/30 text-red-300 border border-red-700";
    if (severity === "medium") return "bg-yellow-900/30 text-yellow-300 border border-yellow-700";
    return "bg-green-900/30 text-green-300 border border-green-700";
  };

  const getMetricTrendColor = (trend: string, current: number, previous: number) => {
    if (trend === "up" && current > previous) return "text-green-400";
    if (trend === "down" && current < previous) return "text-green-400";
    return "text-red-400";
  };

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-900 to-purple-800 border-b border-purple-700 p-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mark size={32} />
            <div>
              <h1 className="text-2xl font-bold text-white">Wellness Consultant Portal</h1>
              <p className="text-purple-200 text-sm">Analytics, Insights & Recommendations</p>
            </div>
          </div>
          <button
            onClick={() => {
              localStorage.removeItem("mgmt_role");
              localStorage.removeItem("mgmt_email");
              localStorage.removeItem("mgmt_token");
              navigate("/management");
            }}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* KPI Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Wellness Score", value: "8.9/10", color: "from-green-600 to-green-700", icon: "💚" },
            { label: "Team Satisfaction", value: "87%", color: "from-blue-600 to-blue-700", icon: "😊" },
            { label: "Burnout Risk Down", value: "29%", color: "from-purple-600 to-purple-700", icon: "📉" },
            { label: "Intervention Success", value: "76%", color: "from-orange-600 to-orange-700", icon: "✅" },
          ].map((kpi, idx) => (
            <div key={idx} className={`bg-gradient-to-br ${kpi.color} p-4 rounded-lg text-white`}>
              <div className="text-3xl mb-2">{kpi.icon}</div>
              <div className="text-2xl font-bold">{kpi.value}</div>
              <div className="text-xs opacity-90">{kpi.label}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Wellness Metrics */}
          <div className="lg:col-span-2">
            <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden mb-6">
              <div className="bg-slate-700 px-6 py-4 border-b border-slate-600">
                <h2 className="text-lg font-semibold text-white">Wellness Metrics Trend</h2>
              </div>
              <div className="divide-y divide-slate-700">
                {WELLNESS_METRICS.map((metric) => (
                  <div
                    key={metric.category}
                    onClick={() => setExpandedMetric(expandedMetric === metric.category ? null : metric.category)}
                    className="p-4 hover:bg-slate-700/50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{getTrendIcon(metric.trend)}</span>
                        <div>
                          <h3 className="font-semibold text-white">{metric.category}</h3>
                          <div className="text-xs text-slate-400">
                            {metric.trend === "up" ? "↑" : metric.trend === "down" ? "↓" : "→"} from{" "}
                            {metric.previous.toFixed(1)}
                          </div>
                        </div>
                      </div>
                      <div className={`text-2xl font-bold ${getMetricTrendColor(metric.trend, metric.current, metric.previous)}`}>
                        {metric.current.toFixed(1)}
                      </div>
                    </div>

                    {expandedMetric === metric.category && (
                      <div className="mt-4 pt-4 border-t border-slate-600 bg-slate-700/20 p-3 rounded">
                        <p className="text-sm text-slate-300">💡 {metric.recommendation}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Monthly Report */}
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-white mb-4">📊 Monthly Performance Summary</h2>
              <div className="space-y-4">
                <div className="bg-green-900/20 border border-green-700 rounded p-4">
                  <h3 className="text-green-300 font-semibold mb-2">✅ Achievements</h3>
                  <ul className="text-sm text-green-200 space-y-1">
                    <li>• Stress levels reduced by 12% month-over-month</li>
                    <li>• Sleep quality improved across all departments</li>
                    <li>• Work-life balance score reached 9.2/10</li>
                    <li>• Burnout risk cases reduced by 29%</li>
                  </ul>
                </div>

                <div className="bg-yellow-900/20 border border-yellow-700 rounded p-4">
                  <h3 className="text-yellow-300 font-semibold mb-2">⚠️ Areas of Focus</h3>
                  <ul className="text-sm text-yellow-200 space-y-1">
                    <li>• Night shift employees still showing elevated burnout risk</li>
                    <li>• Meeting load impacting focus time for 2 employees</li>
                    <li>• 3 employees showing sleep deficit patterns</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Insights & Recommendations */}
          <div>
            <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
              <div className="bg-slate-700 px-4 py-3 border-b border-slate-600">
                <h2 className="font-semibold text-white">🎯 Key Insights</h2>
              </div>
              <div className="divide-y divide-slate-700 max-h-[800px] overflow-y-auto">
                {INSIGHTS.map((insight) => (
                  <button
                    key={insight.id}
                    onClick={() => setSelectedInsight(insight)}
                    className={`w-full text-left px-4 py-3 transition-colors ${
                      selectedInsight?.id === insight.id
                        ? "bg-purple-900/30 border-l-2 border-purple-500"
                        : "hover:bg-slate-700/50"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-semibold whitespace-nowrap ${getSeverityColor(insight.severity)}`}>
                        {insight.severity.toUpperCase()}
                      </span>
                      <div className="flex-1">
                        <div className="font-semibold text-white text-sm">{insight.title}</div>
                        <div className="text-xs text-slate-400 mt-1">
                          {insight.affectedEmployees} employee{insight.affectedEmployees > 1 ? "s" : ""}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Selected Insight Detail */}
        {selectedInsight && (
          <div className="mt-6 bg-gradient-to-r from-purple-900/50 to-purple-800/50 border border-purple-700 rounded-lg p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">{selectedInsight.title}</h3>
                <p className="text-purple-200">{selectedInsight.description}</p>
              </div>
              <span className={`px-3 py-1 rounded text-sm font-semibold whitespace-nowrap ${getSeverityColor(selectedInsight.severity)}`}>
                {selectedInsight.severity.toUpperCase()}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-800/50 border border-slate-700 rounded p-4">
                <h4 className="text-slate-400 text-sm mb-2">Affected Employees</h4>
                <div className="text-2xl font-bold text-white">{selectedInsight.affectedEmployees}</div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700 rounded p-4">
                <h4 className="text-slate-400 text-sm mb-2">Recommendation</h4>
                <p className="text-white text-sm">{selectedInsight.recommendation}</p>
              </div>

              <div className="bg-slate-800/50 border border-slate-700 rounded p-4">
                <h4 className="text-slate-400 text-sm mb-2">Next Action</h4>
                <button className="w-full px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-semibold transition-colors">
                  {selectedInsight.action}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Intervention Programs */}
        <div className="mt-6 bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">🎯 Active Intervention Programs</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { name: "Stress Reduction Program", progress: 72, status: "In Progress" },
              { name: "Sleep Hygiene Workshop", progress: 58, status: "In Progress" },
              { name: "Meeting Optimization Initiative", progress: 45, status: "Planning" },
              { name: "Work-Life Balance Support", progress: 89, status: "Active" },
              { name: "Burnout Recovery Program", progress: 64, status: "In Progress" },
              { name: "Mindfulness & Meditation", progress: 76, status: "Active" },
            ].map((program, idx) => (
              <div key={idx} className="bg-slate-700/50 border border-slate-600 rounded p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-white text-sm">{program.name}</h3>
                  <span className="text-xs px-2 py-1 bg-slate-600 text-slate-300 rounded">{program.status}</span>
                </div>
                <div className="w-full bg-slate-600 rounded-full h-2 mb-2">
                  <div
                    className="bg-gradient-to-r from-purple-500 to-purple-400 h-2 rounded-full transition-all"
                    style={{ width: `${program.progress}%` }}
                  ></div>
                </div>
                <div className="text-xs text-slate-400">{program.progress}% complete</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
