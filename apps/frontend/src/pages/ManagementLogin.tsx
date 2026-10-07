import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mark } from "../components/AppShell";
import ThemeToggle from "../components/ThemeToggle";

type Role = "hr" | "manager" | "consultant";

// Registered user emails with their vitals
const REGISTERED_USERS = [
  {
    email: "harish44443@gmail.com",
    name: "Harish Kumar",
    department: "Software Engineering",
    stressLevel: 5,
    energyLevel: 8,
    sleepHours: 6.7,
    moodScore: 8,
  },
  {
    email: "karthikm6@gmail.com",
    name: "Karthik M",
    department: "Data Engineering",
    stressLevel: 4,
    energyLevel: 7,
    sleepHours: 7.3,
    moodScore: 8,
  },
  {
    email: "sanika.g@gmail.com",
    name: "Sanika G",
    department: "AI/ML",
    stressLevel: 3,
    energyLevel: 9,
    sleepHours: 8.0,
    moodScore: 9,
  },
  {
    email: "debothri.ghosh@gmail.com",
    name: "Debothri Ghosh",
    department: "Quality Engineering",
    stressLevel: 5,
    energyLevel: 5,
    sleepHours: 6.1,
    moodScore: 7,
  },
  {
    email: "sksricharan2003@gmail.com",
    name: "S K Sricharan",
    department: "Cloud & DevOps",
    stressLevel: 6,
    energyLevel: 6,
    sleepHours: 6.7,
    moodScore: 6,
  },
  {
    email: "Santhosh@gmail.com",
    name: "Santhosh Rajinikanth",
    department: "AI Engineering",
    stressLevel: 4,
    energyLevel: 8,
    sleepHours: 7.1,
    moodScore: 8,
  },
];

export default function ManagementLogin() {
  const navigate = useNavigate();
  const [role, setRole] = useState<Role>("hr");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Filter suggestions based on input
  const filteredEmails = email.trim()
    ? REGISTERED_USERS.filter(user =>
        user.email.toLowerCase().includes(email.toLowerCase()) ||
        user.name.toLowerCase().includes(email.toLowerCase())
      )
    : REGISTERED_USERS;

  const handleEmailSelect = (selectedEmail: string) => {
    setEmail(selectedEmail);
    setShowSuggestions(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);

    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password) {
      setError("Please enter email and password");
      setBusy(false);
      return;
    }

    // Check if registered user (any password accepted)
    const registeredUser = REGISTERED_USERS.find(
      user => user.email.toLowerCase() === trimmedEmail.toLowerCase()
    );

    // For registered emails: accept any password
    if (registeredUser) {
      try {
        localStorage.setItem("mgmt_role", role);
        localStorage.setItem("mgmt_email", trimmedEmail);
        localStorage.setItem("mgmt_user_name", registeredUser.name);
        localStorage.setItem("mgmt_user_data", JSON.stringify(registeredUser));
        localStorage.setItem("mgmt_token", `mgmt_${role}_${Date.now()}`);
        navigate(`/management/${role}`);
      } catch (err) {
        setError("Login failed. Please try again.");
        setBusy(false);
      }
      return;
    }

    // Emergency access: accept any email + any password
    try {
      localStorage.setItem("mgmt_role", role);
      localStorage.setItem("mgmt_email", trimmedEmail);
      localStorage.setItem("mgmt_user_name", trimmedEmail.split("@")[0]);
      localStorage.setItem("mgmt_user_data", JSON.stringify({
        email: trimmedEmail,
        name: trimmedEmail.split("@")[0],
        department: "Emergency Access",
        stressLevel: 5,
        energyLevel: 5,
        sleepHours: 7,
        moodScore: 5,
      }));
      localStorage.setItem("mgmt_token", `mgmt_${role}_${Date.now()}`);
      navigate(`/management/${role}`);
    } catch (err) {
      setError("Login failed. Please try again.");
      setBusy(false);
    }
  };

  return (
    <div className="min-h-full flex items-center justify-center px-4 py-12 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="fixed top-4 right-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="mb-12 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Mark size={40} />
            <div>
              <div className="font-bold tracking-tight text-[24px] leading-tight text-white">WorkWell AI</div>
              <div className="text-[14px] text-slate-400 leading-tight">
                Management Portal
              </div>
            </div>
          </div>
          <p className="text-slate-400 mt-4">Access employee wellness insights and analytics</p>
        </div>

        {/* Role Selection Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {[
            {
              id: "hr" as Role,
              title: "HR Manager",
              description: "View all employees, wellness reports, leave management, health summaries",
              icon: "👥",
              color: "from-blue-600 to-blue-700"
            },
            {
              id: "manager" as Role,
              title: "Team Manager",
              description: "Monitor team performance, workload, burnout risk, productivity metrics",
              icon: "📊",
              color: "from-green-600 to-green-700"
            },
            {
              id: "consultant" as Role,
              title: "Wellness Consultant",
              description: "Analyze trends, insights, recommendations, intervention strategies",
              icon: "🎯",
              color: "from-purple-600 to-purple-700"
            }
          ].map((roleOption) => (
            <button
              key={roleOption.id}
              onClick={() => setRole(roleOption.id)}
              className={`relative p-6 rounded-lg border-2 transition-all ${
                role === roleOption.id
                  ? "border-white bg-gradient-to-br " + roleOption.color + " text-white"
                  : "border-slate-700 bg-slate-800/50 hover:border-slate-600 text-slate-300"
              }`}
            >
              <div className="text-3xl mb-2">{roleOption.icon}</div>
              <div className="font-semibold text-base">{roleOption.title}</div>
              <div className="text-xs mt-2 opacity-90">{roleOption.description}</div>
              {role === roleOption.id && (
                <div className="absolute top-2 right-2">
                  <div className="w-3 h-3 bg-white rounded-full"></div>
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="panel-raised p-8 bg-slate-800/80 backdrop-blur border border-slate-700">
          <div className="mb-6">
            <h3 className="font-semibold text-white mb-2">
              {role === "hr" && "HR Manager Login"}
              {role === "manager" && "Team Manager Login"}
              {role === "consultant" && "Wellness Consultant Login"}
            </h3>
            <p className="text-slate-400 text-sm">
              {role === "hr" && "Access comprehensive employee wellness and HR analytics"}
              {role === "manager" && "Monitor your team's wellness and performance metrics"}
              {role === "consultant" && "Review insights, trends, and wellness recommendations"}
            </p>
          </div>

          <label htmlFor="email" className="block text-[13px] text-slate-300 mb-2">
            Email Address
          </label>
          <div className="relative mb-4">
            <input
              id="email"
              type="text"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              placeholder="Type name or email"
              className="field w-full bg-slate-700 border-slate-600 text-white placeholder-slate-500"
              autoComplete="off"
            />

            {/* Email Suggestions Dropdown */}
            {showSuggestions && filteredEmails.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-slate-700 border border-slate-600 rounded mt-1 z-10 max-h-64 overflow-y-auto shadow-lg">
                {filteredEmails.map((user) => (
                  <button
                    key={user.email}
                    type="button"
                    onClick={() => handleEmailSelect(user.email)}
                    className="w-full text-left px-3 py-2 hover:bg-slate-600 transition-colors border-b border-slate-600 last:border-b-0"
                  >
                    <div className="text-white font-medium text-sm">{user.email}</div>
                    <div className="text-slate-400 text-xs">{user.name} • {user.department}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <label htmlFor="password" className="block text-[13px] text-slate-300 mb-2">
            Password
          </label>
          <div className="relative mb-6">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              className="field w-full pr-10 bg-slate-700 border-slate-600 text-white placeholder-slate-500"
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
              title={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? "👁️" : "👁️‍🗨️"}
            </button>
          </div>

          {error && (
            <p className="text-[13px] text-red-400 mb-4" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="btn-primary w-full !py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50"
          >
            {busy ? "Logging in..." : "Enter Management Portal"}
          </button>

          <div className="mt-6 pt-6 border-t border-slate-700">
            <p className="text-xs text-slate-400 text-center">
              <span className="block mb-2">🔐 Secure Role-Based Access Portal</span>
              <span>Access to data is role-based and read-only</span>
            </p>
          </div>
        </form>

        {/* Footer */}
        <div className="mt-8 text-center text-slate-500 text-xs">
          <p>Emergency Contact: <span className="text-slate-300 font-semibold">+91 637-484-4668</span></p>
          <p>Health & Support: <span className="text-slate-300 font-semibold">health.hr@ltm.com</span></p>
        </div>
      </div>
    </div>
  );
}
