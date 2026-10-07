import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Mark } from "../components/AppShell";

interface TeamMember {
  id: string;
  name: string;
  role: string;
  project: string;
  workloadHours: number;
  productivity: number;
  burnoutRisk: "Low" | "Medium" | "High";
  stressLevel: number;
  focusTime: number;
  meetings: number;
  contextSwitches: number;
  tasksCompleted: number;
  performanceRating: number;
  status: "Active" | "WFH" | "Break";
  nextReview: string;
}

const MOCK_TEAM: TeamMember[] = [
  {
    id: "1",
    name: "Harish Kumar",
    role: "Graduate Engineer",
    project: "Retail Analytics Platform",
    workloadHours: 7.75,
    productivity: 96,
    burnoutRisk: "Low",
    stressLevel: 5,
    focusTime: 324,
    meetings: 1.2,
    contextSwitches: 31,
    tasksCompleted: 10,
    performanceRating: 4.0,
    status: "Active",
    nextReview: "2026-10-21",
  },
  {
    id: "2",
    name: "Karthik M",
    role: "Data Engineer",
    project: "ETL Monitoring",
    workloadHours: 4.67,
    productivity: 96,
    burnoutRisk: "Low",
    stressLevel: 4,
    focusTime: 166,
    meetings: 0.6,
    contextSwitches: 21,
    tasksCompleted: 4,
    performanceRating: 4.2,
    status: "Active",
    nextReview: "2026-10-19",
  },
  {
    id: "3",
    name: "Sanika G",
    role: "AI/ML Engineer",
    project: "Document Intelligence",
    workloadHours: 7.42,
    productivity: 96,
    burnoutRisk: "Low",
    stressLevel: 3,
    focusTime: 259,
    meetings: 1.2,
    contextSwitches: 25,
    tasksCompleted: 8,
    performanceRating: 4.4,
    status: "Active",
    nextReview: "2026-10-16",
  },
  {
    id: "4",
    name: "Debothri Ghosh",
    role: "QA Engineer",
    project: "Digital Banking QA",
    workloadHours: 7.88,
    productivity: 85,
    burnoutRisk: "Medium",
    stressLevel: 5,
    focusTime: 269,
    meetings: 1.8,
    contextSwitches: 42,
    tasksCompleted: 6,
    performanceRating: 3.8,
    status: "Active",
    nextReview: "2026-10-28",
  },
];

export default function ManagementManager() {
  const navigate = useNavigate();
  const [team, setTeam] = useState<TeamMember[]>(MOCK_TEAM);
  const [selectedMember, setSelectedMember] = useState<TeamMember | null>(null);
  const [view, setView] = useState<"overview" | "workload" | "performance">("overview");
  const [loggedInUserEmail, setLoggedInUserEmail] = useState("");

  useEffect(() => {
    const role = localStorage.getItem("mgmt_role");
    const userEmail = localStorage.getItem("mgmt_email");

    if (role !== "manager") {
      navigate("/management");
    }

    if (userEmail) {
      setLoggedInUserEmail(userEmail);
      // Select the logged-in user's member data
      const userMember = MOCK_TEAM.find(m => m.name.toLowerCase().includes(userEmail.split("@")[0]));
      if (userMember) {
        setSelectedMember(userMember);
      } else {
        setSelectedMember(MOCK_TEAM[0]);
      }
    }
  }, [navigate]);

  const teamStats = {
    avgProductivity: Math.round(team.reduce((sum, m) => sum + m.productivity, 0) / team.length),
    avgStress: (team.reduce((sum, m) => sum + m.stressLevel, 0) / team.length).toFixed(1),
    highRiskCount: team.filter((m) => m.burnoutRisk === "High").length,
    avgFocusTime: Math.round(team.reduce((sum, m) => sum + m.focusTime, 0) / team.length),
  };

  const getRiskColor = (risk: string) => {
    if (risk === "High") return "bg-red-900/30 text-red-300 border border-red-700";
    if (risk === "Medium") return "bg-yellow-900/30 text-yellow-300 border border-yellow-700";
    return "bg-green-900/30 text-green-300 border border-green-700";
  };

  const getStatusBadgeColor = (status: string) => {
    if (status === "Active") return "bg-green-900/50 text-green-300";
    if (status === "WFH") return "bg-blue-900/50 text-blue-300";
    return "bg-gray-900/50 text-gray-300";
  };

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-900 to-green-800 border-b border-green-700 p-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mark size={32} />
            <div>
              <h1 className="text-2xl font-bold text-white">Manager Dashboard</h1>
              <p className="text-green-200 text-sm">Team Performance & Workload Management</p>
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
        {/* Team Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Avg Productivity", value: `${teamStats.avgProductivity}%`, color: "from-blue-600 to-blue-700" },
            { label: "Avg Stress Level", value: `${teamStats.avgStress}/10`, color: "from-orange-600 to-orange-700" },
            { label: "High Risk Count", value: teamStats.highRiskCount, color: "from-red-600 to-red-700" },
            { label: "Avg Focus Time", value: `${teamStats.avgFocusTime}m`, color: "from-purple-600 to-purple-700" },
          ].map((stat, idx) => (
            <div key={idx} className={`bg-gradient-to-br ${stat.color} p-4 rounded-lg text-white`}>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="text-xs opacity-90">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Team List */}
          <div className="lg:col-span-1">
            <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
              <div className="bg-slate-700 px-4 py-3 border-b border-slate-600">
                <h3 className="font-semibold text-white">Team Members</h3>
              </div>
              <div className="divide-y divide-slate-700 max-h-[600px] overflow-y-auto">
                {team.map((member) => (
                  <button
                    key={member.id}
                    onClick={() => setSelectedMember(member)}
                    className={`w-full text-left px-4 py-3 transition-colors ${
                      selectedMember?.id === member.id
                        ? "bg-green-900/30 border-l-2 border-green-500"
                        : "hover:bg-slate-700/50"
                    }`}
                  >
                    <div className="font-semibold text-white">{member.name}</div>
                    <div className="text-xs text-slate-400">{member.role}</div>
                    <div className="mt-2 flex gap-2">
                      <span className={`text-xs px-2 py-1 rounded ${getRiskColor(member.burnoutRisk)}`}>
                        {member.burnoutRisk}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded ${getStatusBadgeColor(member.status)}`}>
                        {member.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Member Details */}
          <div className="lg:col-span-2">
            {selectedMember && (
              <>
                {/* Tabs */}
                <div className="flex gap-2 mb-4 border-b border-slate-700">
                  {["overview", "workload", "performance"].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setView(tab as any)}
                      className={`px-4 py-2 font-semibold transition-colors ${
                        view === tab
                          ? "text-green-400 border-b-2 border-green-400"
                          : "text-slate-400 hover:text-slate-300"
                      }`}
                    >
                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                  ))}
                </div>

                {/* Overview Tab */}
                {view === "overview" && (
                  <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <h4 className="text-sm text-slate-400 mb-1">Current Project</h4>
                        <div className="text-lg font-semibold text-white">{selectedMember.project}</div>
                      </div>
                      <div>
                        <h4 className="text-sm text-slate-400 mb-1">Status</h4>
                        <div className={`text-lg font-semibold px-3 py-1 rounded inline-block ${getStatusBadgeColor(selectedMember.status)}`}>
                          {selectedMember.status}
                        </div>
                      </div>
                      <div>
                        <h4 className="text-sm text-slate-400 mb-1">Performance Rating</h4>
                        <div className="text-lg font-semibold text-yellow-400">{selectedMember.performanceRating}/5.0</div>
                      </div>
                      <div>
                        <h4 className="text-sm text-slate-400 mb-1">Next Review</h4>
                        <div className="text-lg font-semibold text-white">{selectedMember.nextReview}</div>
                      </div>
                      <div>
                        <h4 className="text-sm text-slate-400 mb-1">Burnout Risk</h4>
                        <span className={`inline-block px-3 py-1 rounded text-sm font-semibold ${getRiskColor(selectedMember.burnoutRisk)}`}>
                          {selectedMember.burnoutRisk}
                        </span>
                      </div>
                      <div>
                        <h4 className="text-sm text-slate-400 mb-1">Stress Level</h4>
                        <div className="text-lg font-semibold text-orange-400">{selectedMember.stressLevel}/10</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Workload Tab */}
                {view === "workload" && (
                  <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                    <div className="space-y-6">
                      <div>
                        <div className="flex justify-between mb-2">
                          <h4 className="text-slate-300">Daily Work Hours</h4>
                          <span className="text-white font-semibold">{selectedMember.workloadHours}h</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-green-500 h-2 rounded-full"
                            style={{ width: `${(selectedMember.workloadHours / 10) * 100}%` }}
                          ></div>
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between mb-2">
                          <h4 className="text-slate-300">Meetings</h4>
                          <span className="text-white font-semibold">{selectedMember.meetings}h</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${(selectedMember.meetings / 5) * 100}%` }}
                          ></div>
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between mb-2">
                          <h4 className="text-slate-300">Focus Time</h4>
                          <span className="text-white font-semibold">{selectedMember.focusTime}m</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-purple-500 h-2 rounded-full"
                            style={{ width: `${(selectedMember.focusTime / 480) * 100}%` }}
                          ></div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-700">
                        <div>
                          <h4 className="text-slate-400 text-sm mb-1">Context Switches</h4>
                          <div className="text-2xl font-bold text-orange-400">{selectedMember.contextSwitches}</div>
                        </div>
                        <div>
                          <h4 className="text-slate-400 text-sm mb-1">Tasks Completed</h4>
                          <div className="text-2xl font-bold text-green-400">{selectedMember.tasksCompleted}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Performance Tab */}
                {view === "performance" && (
                  <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between mb-2">
                          <h4 className="text-slate-300">Productivity Score</h4>
                          <span className="text-white font-semibold">{selectedMember.productivity}%</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-3">
                          <div
                            className="bg-green-500 h-3 rounded-full transition-all"
                            style={{ width: `${selectedMember.productivity}%` }}
                          ></div>
                        </div>
                      </div>

                      <div className="border-t border-slate-700 pt-4">
                        <h4 className="text-slate-300 mb-3">Key Metrics</h4>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-slate-700/50 p-3 rounded">
                            <div className="text-slate-400 text-xs">Performance Rating</div>
                            <div className="text-xl font-bold text-yellow-400">{selectedMember.performanceRating}/5</div>
                          </div>
                          <div className="bg-slate-700/50 p-3 rounded">
                            <div className="text-slate-400 text-xs">Tasks/Day Avg</div>
                            <div className="text-xl font-bold text-blue-400">{selectedMember.tasksCompleted}</div>
                          </div>
                          <div className="bg-slate-700/50 p-3 rounded">
                            <div className="text-slate-400 text-xs">Stress Level</div>
                            <div className="text-xl font-bold text-orange-400">{selectedMember.stressLevel}/10</div>
                          </div>
                          <div className="bg-slate-700/50 p-3 rounded">
                            <div className="text-slate-400 text-xs">Burnout Risk</div>
                            <div className={`text-sm font-bold ${selectedMember.burnoutRisk === "High" ? "text-red-400" : selectedMember.burnoutRisk === "Medium" ? "text-yellow-400" : "text-green-400"}`}>
                              {selectedMember.burnoutRisk}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="bg-blue-900/30 border border-blue-700 rounded p-4">
                        <h4 className="text-blue-300 font-semibold mb-2">💡 Manager Notes</h4>
                        <p className="text-blue-200 text-sm">
                          {selectedMember.performanceRating >= 4
                            ? "Strong performer. Consider for growth opportunities and mentoring roles."
                            : "Moderate performer. Schedule a 1-on-1 to discuss goals and support needs."}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
