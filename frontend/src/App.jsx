import { useState } from "react"
import axios from "axios"

const API = "https://talentmatch-pro-production.up.railway.app/";


const RECOMMENDATION_COLORS = {
  "Strong Yes" : "bg-green-700 text-white",
  "Yes"        : "bg-green-500 text-white",
  "Maybe"      : "bg-yellow-500 text-white",
  "No"         : "bg-red-500 text-white",
}

const RECOMMENDATION_ORDER = {
  "Strong Yes" : 0,
  "Yes"        : 1,
  "Maybe"      : 2,
  "No"         : 3,
}


// ─────────────────────────────────────────────
// FR-08 — PDF EXPORT
// ─────────────────────────────────────────────

function exportToPDF(results) {
  const date     = new Date(results.generated_at).toLocaleString()
  const jd_level = results.jd_parsed?.role_level || "N/A"
  const jd_exp   = results.jd_parsed?.min_experience_years ?? "N/A"
  const jd_edu   = results.jd_parsed?.education_requirement || "N/A"

  const candidateRows = results.candidates.map((c) => `
    <div class="candidate">
      <div class="candidate-header">
        <span class="rank">#${c.rank}</span>
        <span class="name">${c.name}</span>
        <span class="score">${c.match_score}%</span>
        <span class="rec rec-${c.recommendation.replace(" ", "-")}">${c.recommendation}</span>
        ${c.note ? `<span class="note">📝 ${c.note}</span>` : ""}
      </div>
      <p class="summary">${c.fit_summary}</p>
      <div class="two-col">
        <div class="strengths">
          <strong>Strengths</strong>
          ${c.strengths.map(s => `<p>✓ ${s}</p>`).join("")}
        </div>
        <div class="gaps">
          <strong>Gaps</strong>
          ${c.gaps.map(g => `<p>✗ ${g}</p>`).join("")}
        </div>
      </div>
      ${c.bias_flags?.length > 0 ? `
        <div class="flags">
          <strong>⚠ Bias Flags</strong>
          ${c.bias_flags.map(f => `<p>${f.message}</p>`).join("")}
        </div>` : ""}
    </div>
  `).join("")

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>TalentMatch Pro — Shortlist Report</title>
      <style>
        body        { font-family: Arial, sans-serif; color: #1a1a2e; padding: 40px; }
        h1          { color: #1B3A5C; }
        .meta       { display: flex; gap: 40px; margin: 20px 0; padding: 16px; background: #EBF5FB; border-radius: 8px; }
        .meta-item  { text-align: center; }
        .meta-item strong { display: block; font-size: 20px; color: #1B3A5C; }
        .meta-item span   { font-size: 11px; color: #888; text-transform: uppercase; }
        .candidate  { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 12px 0; }
        .candidate-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
        .rank       { font-size: 20px; font-weight: bold; color: #1B3A5C; }
        .name       { font-weight: bold; flex: 1; }
        .score      { font-weight: bold; color: #2E86AB; }
        .rec        { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; color: white; }
        .rec-Strong-Yes { background: #1E8449; }
        .rec-Yes        { background: #27AE60; }
        .rec-Maybe      { background: #F39C12; }
        .rec-No         { background: #C0392B; }
        .note       { font-size: 11px; color: #888; font-style: italic; }
        .summary    { font-size: 13px; color: #444; margin: 8px 0; }
        .two-col    { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 8px 0; }
        .strengths  { background: #EAFAF1; padding: 10px; border-radius: 6px; font-size: 12px; }
        .gaps       { background: #FDEDEC; padding: 10px; border-radius: 6px; font-size: 12px; }
        .flags      { background: #FEFCE8; padding: 10px; border-radius: 6px; font-size: 12px; margin-top: 8px; }
        .footer     { color: #aaa; font-size: 11px; margin-top: 40px; text-align: center; }
        @media print { body { padding: 20px; } }
      </style>
    </head>
    <body>
      <h1>TalentMatch Pro — Shortlist Report</h1>
      <p style="color:#888; font-size:13px;">Generated: ${date}</p>

      <div class="meta">
        <div class="meta-item"><strong>${results.total_screened}</strong><span>CVs Screened</span></div>
        <div class="meta-item"><strong>${results.candidates.length}</strong><span>Shortlisted</span></div>
        <div class="meta-item"><strong>${jd_level}</strong><span>Role Level</span></div>
        <div class="meta-item"><strong>${jd_exp}</strong><span>Min Years</span></div>
        <div class="meta-item"><strong>${jd_edu}</strong><span>Education</span></div>
      </div>

      ${candidateRows}

      <p class="footer">
        TalentMatch Pro — AI-powered CV Screening · Confidential<br/>
        © 2026 TalentMatch Pro. All rights reserved.
      </p>
    </body>
    </html>
  `

  const win = window.open("", "_blank")
  win.document.write(html)
  win.document.close()
  win.print()
}


// ─────────────────────────────────────────────
// FOOTER COMPONENT
// Shared between both screens
// ─────────────────────────────────────────────

function Footer() {
  return (
    <p className="text-center text-xs text-gray-400 mt-10 pb-6">
      © 2026 TalentMatch Pro. All rights reserved.
    </p>
  )
}


// ─────────────────────────────────────────────
// UPLOAD SCREEN
// ─────────────────────────────────────────────

function UploadScreen({ onResults }) {
  const [jdText,  setJdText]  = useState("")
  const [files,   setFiles]   = useState([])
  const [loading, setLoading] = useState(false)
  const [status,  setStatus]  = useState("")
  const [error,   setError]   = useState("")

  async function runScreening() {
    if (!jdText.trim())     return setError("Please paste a Job Description.")
    if (files.length === 0) return setError("Please upload at least one CV.")

    setError("")
    setLoading(true)

    try {
      setStatus("Creating session...")
      const { data: session } = await axios.post(`${API}/session/create`)
      const sid = session.session_id

      setStatus(`Uploading ${files.length} CVs...`)
      const formData = new FormData()
      for (const file of files) formData.append("files", file)
      await axios.post(`${API}/session/${sid}/upload-cvs`, formData)

      setStatus("Saving job description...")
      await axios.post(`${API}/session/${sid}/set-jd`, {
        jd_text : jdText,
        top_n   : 20
      })

      setStatus("Ranking candidates and generating AI reasoning — please wait (~60 sec)...")
      const { data: results } = await axios.post(
        `${API}/session/${sid}/rank`,
        {},
        { timeout: 300000 }
      )

      onResults(results)

    } catch (err) {
      setError(`Error: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
      setStatus("")
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-3xl">

        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-blue-900 mb-2">TalentMatch Pro</h1>
          <p className="text-gray-500">AI-powered CV Ranking & Screening</p>
        </div>

        {/* JD Input */}
        <div className="bg-white rounded-2xl shadow p-6 mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Job Description
          </label>
          <textarea
            rows={8}
            placeholder="Paste the full job description here..."
            value={jdText}
            onChange={e => setJdText(e.target.value)}
            className="w-full border border-gray-200 rounded-xl p-4 text-sm text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* CV Upload */}
        <div className="bg-white rounded-2xl shadow p-6 mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Upload CVs (PDF only)
          </label>
          <input
            type="file"
            multiple
            accept=".pdf"
            onChange={e => setFiles(Array.from(e.target.files))}
            className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          {files.length > 0 && (
            <p className="mt-2 text-sm text-green-600 font-medium">
              ✓ {files.length} CV{files.length > 1 ? "s" : ""} selected
            </p>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Status */}
        {loading && (
          <div className="bg-blue-50 border border-blue-200 text-blue-700 rounded-xl p-4 mb-4 text-sm flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            {status}
          </div>
        )}

        {/* Run button */}
        <button
          onClick={runScreening}
          disabled={loading}
          className="w-full bg-blue-900 hover:bg-blue-800 disabled:bg-gray-300 text-white font-semibold py-4 rounded-2xl text-lg transition-colors"
        >
          {loading ? "Processing..." : "Run Screening"}
        </button>

        {/* Footer */}
        <Footer />

      </div>
    </div>
  )
}


// ─────────────────────────────────────────────
// CANDIDATE CARD
// FR-07: collapsible reasoning panel + notes
// ─────────────────────────────────────────────

function CandidateCard({ candidate, rank, onNoteChange }) {
  const [expanded, setExpanded] = useState(false)
  const [note,     setNote]     = useState(candidate.note || "")
  const recColor = RECOMMENDATION_COLORS[candidate.recommendation] || "bg-gray-400 text-white"

  function handleNoteBlur() {
    onNoteChange(candidate.filename, note)
  }

  return (
    <div className="bg-white rounded-2xl shadow mb-4 overflow-hidden">

      {/* Header row */}
      <div
        className="flex items-center justify-between p-5 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold text-blue-900 w-8">#{rank}</span>
          <div>
            <p className="font-semibold text-gray-800">{candidate.name}</p>
            <p className="text-xs text-gray-400">{candidate.filename}</p>
            {candidate.note && (
              <p className="text-xs text-blue-600 mt-0.5">📝 {candidate.note}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-blue-700">{candidate.match_score}%</span>
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${recColor}`}>
            {candidate.recommendation}
          </span>
          <span className="text-gray-400 text-sm">{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {/* Expanded panel */}
      {expanded && (
        <div className="border-t border-gray-100 p-5 bg-gray-50">

          <p className="text-sm text-gray-700 mb-4 leading-relaxed">
            {candidate.fit_summary}
          </p>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-green-50 rounded-xl p-4">
              <p className="text-xs font-bold text-green-700 mb-2 uppercase tracking-wide">
                Strengths
              </p>
              {candidate.strengths.length > 0
                ? candidate.strengths.map((s, i) => (
                    <p key={i} className="text-xs text-green-800 mb-1">✓ {s}</p>
                  ))
                : <p className="text-xs text-gray-400">None identified</p>
              }
            </div>
            <div className="bg-red-50 rounded-xl p-4">
              <p className="text-xs font-bold text-red-700 mb-2 uppercase tracking-wide">
                Gaps
              </p>
              {candidate.gaps.length > 0
                ? candidate.gaps.map((g, i) => (
                    <p key={i} className="text-xs text-red-800 mb-1">✗ {g}</p>
                  ))
                : <p className="text-xs text-gray-400">None identified</p>
              }
            </div>
          </div>

          {candidate.bias_flags?.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-4">
              <p className="text-xs font-bold text-yellow-700 mb-2 uppercase tracking-wide">
                ⚠ Bias Awareness Flags
              </p>
              {candidate.bias_flags.map((flag, i) => (
                <p key={i} className="text-xs text-yellow-800 mb-1">{flag.message}</p>
              ))}
            </div>
          )}

          <div className="mt-2">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1 block">
              Recruiter Notes
            </label>
            <textarea
              rows={2}
              placeholder="Add notes about this candidate..."
              value={note}
              onChange={e => setNote(e.target.value)}
              onBlur={handleNoteBlur}
              onClick={e => e.stopPropagation()}
              className="w-full border border-gray-200 rounded-xl p-3 text-sm text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>

        </div>
      )}
    </div>
  )
}


// ─────────────────────────────────────────────
// RESULTS SCREEN
// FR-07: sortable + drag override
// FR-08: export button
// ─────────────────────────────────────────────

function ResultsScreen({ results, onBack }) {
  const [candidates, setCandidates] = useState(results.candidates)
  const [sortBy,     setSortBy]     = useState("rank")
  const [dragIdx,    setDragIdx]    = useState(null)

  function sortedCandidates() {
    const list = [...candidates]
    if (sortBy === "rank")  return list
    if (sortBy === "score") return list.sort((a, b) => b.match_score - a.match_score)
    if (sortBy === "recommendation") {
      return list.sort((a, b) =>
        (RECOMMENDATION_ORDER[a.recommendation] ?? 4) -
        (RECOMMENDATION_ORDER[b.recommendation] ?? 4)
      )
    }
    return list
  }

  function handleDragStart(index) {
    setDragIdx(index)
  }

  function handleDragOver(e, index) {
    e.preventDefault()
    if (dragIdx === null || dragIdx === index) return
    const reordered = [...candidates]
    const [moved]   = reordered.splice(dragIdx, 1)
    reordered.splice(index, 0, moved)
    reordered.forEach((c, i) => c.rank = i + 1)
    setCandidates(reordered)
    setDragIdx(index)
  }

  function handleDragEnd() {
    setDragIdx(null)
  }

  function handleNoteChange(filename, note) {
    setCandidates(prev =>
      prev.map(c => c.filename === filename ? { ...c, note } : c)
    )
  }

  function handleExport() {
    exportToPDF({ ...results, candidates: sortedCandidates() })
  }

  const sorted = sortedCandidates()

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-blue-900">Screening Results</h1>
            <p className="text-gray-500 text-sm mt-1">
              {results.total_screened} CVs screened · Top {candidates.length} shown ·{" "}
              {new Date(results.generated_at).toLocaleString()}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleExport}
              className="bg-green-700 hover:bg-green-600 text-white px-4 py-2 rounded-xl text-sm font-semibold"
            >
              ↓ Export PDF
            </button>
            <button
              onClick={onBack}
              className="bg-white border border-gray-200 text-gray-600 px-4 py-2 rounded-xl text-sm hover:bg-gray-50"
            >
              ← New Screening
            </button>
          </div>
        </div>

        {/* Session bias flag */}
        {results.session_flags?.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-4 mb-6">
            <p className="text-sm font-bold text-yellow-700 mb-1">⚠ Session Bias Awareness</p>
            {results.session_flags.map((flag, i) => (
              <p key={i} className="text-sm text-yellow-800">{flag.message}</p>
            ))}
          </div>
        )}

        {/* JD metadata */}
        <div className="bg-white rounded-2xl shadow p-5 mb-6 grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-blue-900">
              {results.jd_parsed?.role_level || "N/A"}
            </p>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Role Level</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-900">
              {results.jd_parsed?.min_experience_years ?? "N/A"}
            </p>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Min Years Req.</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-900">
              {results.jd_parsed?.education_requirement || "N/A"}
            </p>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Education Req.</p>
          </div>
        </div>

        {/* Sort controls */}
        <div className="flex items-center gap-3 mb-4">
          <span className="text-sm text-gray-500 font-medium">Sort by:</span>
          {["rank", "score", "recommendation"].map(opt => (
            <button
              key={opt}
              onClick={() => setSortBy(opt)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                sortBy === opt
                  ? "bg-blue-900 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {opt.charAt(0).toUpperCase() + opt.slice(1)}
            </button>
          ))}
          <span className="text-xs text-gray-400 ml-2">
            Drag cards to manually reorder
          </span>
        </div>

        {/* Candidate cards */}
        {sorted.map((candidate, i) => (
          <div
            key={candidate.filename}
            draggable
            onDragStart={() => handleDragStart(i)}
            onDragOver={e => handleDragOver(e, i)}
            onDragEnd={handleDragEnd}
            className={`transition-opacity ${dragIdx === i ? "opacity-50" : "opacity-100"}`}
          >
            <CandidateCard
              candidate={candidate}
              rank={candidate.rank}
              onNoteChange={handleNoteChange}
            />
          </div>
        ))}

        {/* Footer */}
        <Footer />

      </div>
    </div>
  )
}


// ─────────────────────────────────────────────
// MAIN APP
// ─────────────────────────────────────────────

export default function App() {
  const [results, setResults] = useState(null)

  return results
    ? <ResultsScreen results={results} onBack={() => setResults(null)} />
    : <UploadScreen  onResults={setResults} />
}