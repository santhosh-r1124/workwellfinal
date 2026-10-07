import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Mark } from "../components/AppShell";
import PageHeader from "../components/PageHeader";

interface Employee {
  id: string;
  email: string;
  name: string;
  department: string;
  designation: string;
  stressLevel: number;
  energyLevel: number;
  sleepHours: number;
  moodScore: number;
  burnoutRisk: "Low" | "Medium" | "High";
  workLifeBalance: number;
  mentalHealthScore: number;
  attendance: number;
  recentActivity: string;
  leaveBalance: number;
}

const MOCK_EMPLOYEES: Employee[] = [
  {
    id: "1",
    email: "harish44443@gmail.com",
    name: "Harish Kumar",
    department: "Software Engineering",
    designation: "Graduate Engineer Trainee",
    stressLevel: 5,
    energyLevel: 8,
    sleepHours: 6.7,
    moodScore: 8,
    burnoutRisk: "Low",
    workLifeBalance: 9,
    mentalHealthScore: 10,
    attendance: 96,
    recentActivity: "Active - Retail Analytics Platform",
    leaveBalance: 10,
  },
  {
    id: "2",
    email: "karthikm6@gmail.com",
    name: "Karthik M",
    department: "Data Engineering",
    designation: "Data Engineering Trainee",
    stressLevel: 4,
    energyLevel: 7,
    sleepHours: 7.3,
    moodScore: 8,
    burnoutRisk: "Low",
    workLifeBalance: 10,
    mentalHealthScore: 10,
    attendance: 94,
    recentActivity: "Active - ETL Monitoring",
    leaveBalance: 12,
  },
  {
    id: "3",
    email: "sanika.g@gmail.com",
    name: "Sanika G",
    department: "AI/ML",
    designation: "AI/ML Trainee",
    stressLevel: 3,
    energyLevel: 9,
    sleepHours: 8.0,
    moodScore: 9,
    burnoutRisk: "Low",
    workLifeBalance: 10,
    mentalHealthScore: 10,
    attendance: 98,
    recentActivity: "Active - Document Intelligence",
    leaveBalance: 11,
  },
  {
    id: "4",
    email: "debothri.ghosh@gmail.com",
    name: "Debothri Ghosh",
    department: "Quality Engineering",
    designation: "QA Automation Trainee",
    stressLevel: 5,
    energyLevel: 5,
    sleepHours: 6.1,
    moodScore: 7,
    burnoutRisk: "Medium",
    workLifeBalance: 8,
    mentalHealthScore: 9,
    attendance: 92,
    recentActivity: "Active - Digital Banking QA",
    leaveBalance: 13,
  },
  {
    id: "5",
    email: "sksricharan2003@gmail.com",
    name: "S K Sricharan",
    department: "Cloud & DevOps",
    designation: "Cloud Operations Trainee",
    stressLevel: 6,
    energyLevel: 6,
    sleepHours: 6.7,
    moodScore: 6,
    burnoutRisk: "Medium",
    workLifeBalance: 9,
    mentalHealthScore: 8,
    attendance: 93,
    recentActivity: "Active - Azure Migration Support",
    leaveBalance: 9,
  },
  {
    id: "6",
    email: "Santhosh@gmail.com",
    name: "Santhosh Rajinikanth",
    department: "AI Engineering",
    designation: "AI Engineer Trainee",
    stressLevel: 4,
    energyLevel: 8,
    sleepHours: 7.1,
    moodScore: 8,
    burnoutRisk: "Low",
    workLifeBalance: 10,
    mentalHealthScore: 10,
    attendance: 97,
    recentActivity: "Active - Employee Wellness AI",
    leaveBalance: 10,
  },
];

export default function ManagementHR() {
  const navigate = useNavigate();
  const [employees, setEmployees] = useState<Employee[]>(MOCK_EMPLOYEES);
  const [filter, setFilter] = useState<"all" | "high" | "medium" | "low">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"name" | "burnout" | "stress" | "attendance">("name");
  const [loggedInUserEmail, setLoggedInUserEmail] = useState("");

  useEffect(() => {
    const role = localStorage.getItem("mgmt_role");
    const userEmail = localStorage.getItem("mgmt_email");

    if (role !== "hr") {
      navigate("/management");
    }

    if (userEmail) {
      setLoggedInUserEmail(userEmail);
    }
  }, [navigate]);

  const filteredEmployees = employees
    .filter((emp) => {
      if (filter !== "all" && emp.burnoutRisk.toLowerCase() !== filter) return false;
      if (searchQuery && !emp.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
          !emp.email.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    })
    .sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name);
      if (sortBy === "burnout") {
        const riskOrder = { High: 3, Medium: 2, Low: 1 };
        return riskOrder[b.burnoutRisk] - riskOrder[a.burnoutRisk];
      }
      if (sortBy === "stress") return b.stressLevel - a.stressLevel;
      if (sortBy === "attendance") return a.attendance - b.attendance;
      return 0;
    });

  const stats = {
    totalEmployees: employees.length,
    highRisk: employees.filter((e) => e.burnoutRisk === "High").length,
    mediumRisk: employees.filter((e) => e.burnoutRisk === "Medium").length,
    avgAttendance: Math.round(employees.reduce((sum, e) => sum + e.attendance, 0) / employees.length),
    avgWorkLifeBalance: Math.round(employees.reduce((sum, e) => sum + e.workLifeBalance, 0) / employees.length),
  };

  const getRiskColor = (risk: string) => {
    if (risk === "High") return "bg-red-900/20 text-red-300 border-red-700";
    if (risk === "Medium") return "bg-yellow-900/20 text-yellow-300 border-yellow-700";
    return "bg-green-900/20 text-green-300 border-green-700";
  };

  const getScoreColor = (score: number) => {
    if (score >= 8) return "text-green-400";
    if (score >= 6) return "text-yellow-400";
    return "text-red-400";
  };

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-900 to-blue-800 border-b border-blue-700 p-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mark size={32} />
            <div>
              <h1 className="text-2xl font-bold text-white">HR Management Portal</h1>
              <p className="text-blue-200 text-sm">Employee Wellness & Performance Overview</p>
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
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          {[
            { label: "Total Employees", value: stats.totalEmployees, color: "from-blue-600 to-blue-700" },
            { label: "High Risk", value: stats.highRisk, color: "from-red-600 to-red-700" },
            { label: "Medium Risk", value: stats.mediumRisk, color: "from-yellow-600 to-yellow-700" },
            { label: "Avg Attendance", value: `${stats.avgAttendance}%`, color: "from-green-600 to-green-700" },
            { label: "Avg Work-Life Balance", value: `${stats.avgWorkLifeBalance}/10`, color: "from-purple-600 to-purple-700" },
          ].map((stat, idx) => (
            <div key={idx} className={`bg-gradient-to-br ${stat.color} p-4 rounded-lg text-white`}>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="text-xs opacity-90">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Filters & Search */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-slate-300 mb-2">Search Employee</label>
              <input
                type="text"
                placeholder="Name or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-2">Filter by Risk</label>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:border-blue-500"
              >
                <option value="all">All Risks</option>
                <option value="high">High Risk Only</option>
                <option value="medium">Medium Risk Only</option>
                <option value="low">Low Risk Only</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-2">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:border-blue-500"
              >
                <option value="name">Name</option>
                <option value="burnout">Burnout Risk</option>
                <option value="stress">Stress Level</option>
                <option value="attendance">Attendance</option>
              </select>
            </div>
          </div>
        </div>

        {/* Employees Table */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-700 border-b border-slate-600">
                <tr>
                  <th className="px-4 py-3 text-left text-slate-300 font-semibold">Employee</th>
                  <th className="px-4 py-3 text-left text-slate-300 font-semibold">Department</th>
                  <th className="px-4 py-3 text-center text-slate-300 font-semibold">Burnout Risk</th>
                  <th className="px-4 py-3 text-center text-slate-300 font-semibold">Stress</th>
                  <th className="px-4 py-3 text-center text-slate-300 font-semibold">Mood</th>
                  <th className="px-4 py-3 text-center text-slate-300 font-semibold">Sleep</th>
                  <th className="px-4 py-3 text-center text-slate-300 font-semibold">Work-Life</th>
                  <th className="px-4 py-3 text-center text-slate-300 font-semibold">Attendance</th>
                  <th className="px-4 py-3 text-center text-slate-300 font-semibold">Leave</th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp) => (
                  <tr key={emp.id} className="border-b border-slate-700 hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <div>
                        <div className="font-semibold text-white">{emp.name}</div>
                        <div className="text-xs text-slate-400">{emp.email}</div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{emp.department}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-block px-3 py-1 rounded text-xs font-semibold border ${getRiskColor(emp.burnoutRisk)}`}>
                        {emp.burnoutRisk}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-semibold ${getScoreColor(emp.stressLevel)}`}>{emp.stressLevel}/10</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-semibold ${getScoreColor(emp.moodScore)}`}>{emp.moodScore}/10</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-slate-300">{emp.sleepHours}h</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-semibold ${getScoreColor(emp.workLifeBalance)}`}>{emp.workLifeBalance}/10</span>
                    </td>
                    <td className="px-4 py-3 text-center text-slate-300">{emp.attendance}%</td>
                    <td className="px-4 py-3 text-center text-slate-300">{emp.leaveBalance} days</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {filteredEmployees.length === 0 && (
          <div className="text-center py-8 text-slate-400">
            No employees found matching your criteria
          </div>
        )}
      </div>
    </div>
  );
}
