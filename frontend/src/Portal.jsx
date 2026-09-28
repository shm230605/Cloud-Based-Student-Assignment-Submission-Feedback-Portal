import { useEffect, useState } from 'react'
import {
  ArrowDownToLine, ArrowUpRight, BookOpen, Check, ChevronDown, Clock3, Cloud,
  FilePlus2, FileText, LogOut, Menu, Plus, Search, ShieldCheck, Sparkles,
  UploadCloud, Users, X,
} from 'lucide-react'
import { api, clearSession, getSession, saveSession } from './services/api.js'

const emptyDashboard = { total_assignments: 0, pending_assignments: 0, submitted_assignments: 0, late_submissions: 0, graded_submissions: 0, total_students: 0, total_submissions: 0, pending_reviews: 0, recent_submissions: [], assignments: [] }
const dateLabel = (value) => new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(value))
const dateTimeLabel = (value) => new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(value))
const bytesLabel = (size) => size < 1024 * 1024 ? `${Math.max(1, Math.round(size / 1024))} KB` : `${(size / 1024 / 1024).toFixed(1)} MB`

function SignIn({ onSignIn }) {
  const [registerMode, setRegisterMode] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('teacher@example.edu')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  function changeMode(nextRegisterMode) {
    setRegisterMode(nextRegisterMode)
    setPassword('')
    setError('')
    if (nextRegisterMode) {
      setName('')
      setEmail('')
    } else {
      setEmail('teacher@example.edu')
    }
  }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const session = await api(registerMode ? '/auth/register' : '/auth/login', {
        method: 'POST',
        body: registerMode ? { name, email, password } : { email, password },
        auth: false,
      })
      saveSession(session); onSignIn(session.user)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <main className="login-page">
    <section className="login-visual">
      <div className="visual-top"><span className="brand-mark"><Cloud size={19} /></span><span>FIELDNOTE <i>LEARNING</i></span></div>
      <div className="visual-copy"><div className="eyebrow"><span /> CLASSROOM, CONNECTED</div><h1>Good work<br />deserves a<br /><em>clearer path.</em></h1><p>One calm place for coursework, thoughtful feedback, and every version in between.</p></div>
      <div className="visual-footer"><span>01 / LEARN</span><span>Built for the work behind the work</span></div><div className="orbit orbit-one" /><div className="orbit orbit-two" />
    </section>
    <section className="login-panel"><div className="login-mobile-brand"><span className="brand-mark"><Cloud size={18} /></span> FIELDNOTE</div><div className="login-form-wrap">
      <div className="auth-tabs" role="tablist" aria-label="Account access"><button type="button" role="tab" aria-selected={!registerMode} className={!registerMode ? 'active' : ''} onClick={() => changeMode(false)}>Sign in</button><button type="button" role="tab" aria-selected={registerMode} className={registerMode ? 'active' : ''} onClick={() => changeMode(true)}>Create account</button></div>
      <div className="eyebrow muted">{registerMode ? 'NEW STUDENT ACCOUNT' : 'YOUR LEARNING SPACE'}</div><h2>{registerMode ? 'Join your class.' : 'Welcome back.'}</h2><p className="login-intro">{registerMode ? 'Create your student account to access coursework and feedback.' : 'One secure sign-in for students and faculty.'}</p>
      <form onSubmit={submit} className="login-form">{registerMode && <label>Your name<input value={name} onChange={(event) => setName(event.target.value)} required minLength="2" autoComplete="name" /></label>}<label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="username" /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={registerMode ? 'At least 10 characters' : 'Use the password from your local environment'} required minLength={registerMode ? 10 : undefined} autoComplete={registerMode ? 'new-password' : 'current-password'} /></label>{error && <div className="inline-error">{error}</div>}<button className="button button-dark full-button" disabled={busy}>{busy ? 'Please wait…' : registerMode ? 'Create student account' : 'Sign in'} <ArrowUpRight size={16} /></button></form>
      <div className="account-note"><ShieldCheck size={16} /><span>{registerMode ? 'Faculty access is provisioned by a course administrator.' : 'Your dashboard and permissions are matched to your account.'}</span></div>
      {!registerMode && <div className="demo-access"><ShieldCheck size={16} /><div><b>Demo workspace</b><span>Use the seeded teacher or student account from your local environment setup.</span></div></div>}<div className="login-legal">PRIVATE BY DEFAULT <span>·</span> YOUR CLASS, YOUR WORK</div>
    </div></section>
  </main>
}

function Portal() {
  const [user, setUser] = useState(() => getSession()?.user ?? null)
  const [dashboard, setDashboard] = useState(emptyDashboard)
  const [submissions, setSubmissions] = useState([])
  const [courses, setCourses] = useState([])
  const [selectedAssignment, setSelectedAssignment] = useState(null)
  const [file, setFile] = useState(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [search, setSearch] = useState('')
  const [gradeDrafts, setGradeDrafts] = useState({})

  async function refresh() {
    const data = await api('/dashboard'); setDashboard(data)
    if (user?.role === 'student') setSubmissions(await api('/submissions/me'))
    else {
      const courseRows = await api('/courses'); setCourses(courseRows)
      const results = await Promise.all(data.assignments.map((assignment) => api(`/assignments/${assignment.id}/submissions`)))
      setSubmissions(results.flat().sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at)))
    }
  }
  useEffect(() => { if (user) refresh().catch((err) => setError(err.message)) }, [user?.id])
  async function logout() {
    try { await api('/auth/logout', { method: 'POST' }) } catch { /* clear client session even if offline */ }
    clearSession(); setUser(null)
  }
  async function upload(event, assignment) {
    event.preventDefault()
    if (!file) return setError('Choose a file to submit first.')
    setBusy(true); setError(''); setNotice('')
    try {
      const body = new FormData(); body.append('file', file)
      await api(`/assignments/${assignment.id}/submit`, { method: 'POST', body, headers: { 'Idempotency-Key': crypto.randomUUID() } })
      setNotice(`“${assignment.title}” was submitted successfully.`); setFile(null); setSelectedAssignment(null); await refresh()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  async function grade(submission) {
    const draft = gradeDrafts[submission.id] ?? { marks: '', feedback: '' }
    setBusy(true); setError(''); setNotice('')
    try {
      await api(`/submissions/${submission.id}/grade`, { method: 'POST', body: { marks: Number(draft.marks), feedback: draft.feedback } })
      setNotice(`Feedback saved for ${submission.student_name}.`); await refresh()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  async function download(submission) {
    try {
      const response = await api(`/submissions/${submission.id}/download`, { raw: true })
      const url = URL.createObjectURL(await response.blob()); const anchor = document.createElement('a')
      anchor.href = url; anchor.download = submission.file_name; anchor.click(); URL.revokeObjectURL(url)
    } catch (err) { setError(err.message) }
  }
  if (!user) return <SignIn onSignIn={setUser} />
  const isTeacher = user.role === 'teacher'
  const activeAssignment = dashboard.assignments.find((item) => item.id === selectedAssignment)
  const filteredSubmissions = submissions.filter((submission) => `${submission.file_name} ${submission.assignment_title} ${submission.student_name}`.toLowerCase().includes(search.toLowerCase()))
  const stats = isTeacher ? [
    { label: 'Assignments', value: dashboard.total_assignments, icon: FileText, tone: 'moss', foot: 'In your courses' },
    { label: 'Students', value: dashboard.total_students, icon: Users, tone: 'lavender', foot: 'Registered learners' },
    { label: 'To review', value: dashboard.pending_reviews, icon: Clock3, tone: 'amber', foot: 'Awaiting feedback' },
    { label: 'Graded', value: dashboard.graded_submissions, icon: Check, tone: 'blue', foot: 'Feedback delivered' },
  ] : [
    { label: 'Coursework', value: dashboard.total_assignments, icon: BookOpen, tone: 'moss', foot: 'Across your courses' },
    { label: 'To submit', value: dashboard.pending_assignments, icon: FilePlus2, tone: 'amber', foot: 'Keep an eye on dates' },
    { label: 'Submitted', value: dashboard.submitted_assignments, icon: UploadCloud, tone: 'blue', foot: 'Latest versions' },
    { label: 'Feedback', value: dashboard.graded_submissions, icon: Sparkles, tone: 'lavender', foot: `${dashboard.late_submissions} late submission${dashboard.late_submissions === 1 ? '' : 's'}` },
  ]

  return <div className="app-shell"><aside className="sidebar">
    <a className="side-brand" href="#home"><span className="brand-mark"><Cloud size={18} /></span><span>FIELDNOTE<small>LEARNING PORTAL</small></span></a><div className="sidebar-label">WORKSPACE</div>
    <nav className="side-nav"><a className="nav-item selected" href="#home"><span className="nav-icon"><BookOpen size={17} /></span>Overview</a><a className="nav-item" href="#coursework"><span className="nav-icon"><FileText size={17} /></span>{isTeacher ? 'Assignments' : 'Coursework'}<span className="nav-count">{dashboard.assignments.length}</span></a><a className="nav-item" href="#submissions"><span className="nav-icon"><UploadCloud size={17} /></span>{isTeacher ? 'Submissions' : 'My submissions'}</a></nav>
    <div className="sidebar-bottom"><div className="storage-note"><div className="storage-icon"><ShieldCheck size={17} /></div><b>Private by design</b><p>Course files are protected and only shared with the right people.</p><span className="storage-status"><i /> STORAGE ENCRYPTED</span></div><button className="profile-button" onClick={logout}><span className="avatar">{user.name.split(' ').map((part) => part[0]).slice(0, 2).join('')}</span><span><b>{user.name}</b><small>{isTeacher ? 'Faculty account' : 'Student account'}</small></span><LogOut className="logout-icon" size={16} /></button></div>
  </aside><main className="main-area" id="home"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> Overview</div><div className="topbar-right"><span className="today-label">{new Intl.DateTimeFormat('en', { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date())}</span><span className="top-avatar">{user.name.slice(0, 1)}</span></div></header>
    <div className="content-wrap"><section className="welcome-row"><div><div className="eyebrow muted">{isTeacher ? 'FACULTY WORKSPACE' : 'STUDENT WORKSPACE'} <span className="live-dot" /></div><h1>{isTeacher ? 'Your classroom, in view.' : `Good morning, ${user.name.split(' ')[0]}.`}</h1><p>{isTeacher ? 'A thoughtful overview of coursework and the work waiting for your review.' : 'Here’s what’s happening across your coursework this week.'}</p></div><div className="welcome-actions">{isTeacher && <button className="button button-dark" onClick={() => document.getElementById('create-assignment')?.scrollIntoView({ behavior: 'smooth' })}><Plus size={17} /> New assignment</button>}<div className="class-chip"><span className="class-monogram">CS</span><span><b>Cloud Systems</b><small>Spring semester</small></span><ChevronDown size={15} /></div></div></section>
      {(error || notice) && <div className={`alert ${error ? 'alert-error' : 'alert-success'}`}><span>{error || notice}</span><button onClick={() => { setError(''); setNotice('') }} aria-label="Dismiss"><X size={16} /></button></div>}
      <section className="stats-grid" aria-label="Classroom statistics">{stats.map((stat) => <article className="stat-card" key={stat.label}><div className="stat-top"><span>{stat.label}</span><span className={`stat-icon ${stat.tone}`}><stat.icon size={17} /></span></div><div className="stat-value">{stat.value.toString().padStart(2, '0')}</div><div className="stat-foot">{stat.foot}</div></article>)}</section>
      <div className="workspace-grid"><section className="panel coursework-panel" id="coursework"><div className="panel-heading"><div><div className="eyebrow muted">{isTeacher ? 'COURSE MANAGEMENT' : 'YOUR COURSEWORK'}</div><h2>{isTeacher ? 'Assignments' : 'Upcoming work'}</h2></div><span className="subtle-count">{dashboard.assignments.length} total</span></div>
        <div className="assignment-list">{dashboard.assignments.map((assignment, index) => {
          const own = submissions.filter((item) => item.assignment_id === assignment.id).sort((a, b) => b.version - a.version)[0]
          return <article className="assignment-row" key={assignment.id}><div className={`assignment-index index-${index % 3}`}>{String(index + 1).padStart(2, '0')}</div><div className="assignment-details"><div className="assignment-kicker">{assignment.course_code} <span>·</span> {assignment.course_name}</div><h3>{assignment.title}</h3><p>{assignment.description}</p><div className="assignment-meta"><span><Clock3 size={14} /> Due {dateLabel(assignment.deadline)}</span><span>{assignment.max_marks} pts</span></div></div><div className="assignment-action">{isTeacher ? <span className="review-count">{submissions.filter((item) => item.assignment_id === assignment.id && item.status !== 'GRADED').length} to review</span> : own ? <span className={`status-pill ${own.status.toLowerCase()}`}>{own.status === 'GRADED' ? 'Graded' : own.status === 'LATE' ? 'Late' : 'Submitted'}</span> : <button className="text-button" onClick={() => { setSelectedAssignment(assignment.id); document.getElementById('upload-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' }) }}>Submit <ArrowUpRight size={15} /></button>}</div></article>
        })}{dashboard.assignments.length === 0 && <div className="empty-state">No assignments yet. Your new coursework will appear here.</div>}</div>
        {!isTeacher && dashboard.assignments.some((assignment) => !submissions.some((item) => item.assignment_id === assignment.id)) && <div className="inline-upload" id="upload-form"><div className="upload-heading"><div className="upload-symbol"><UploadCloud size={18} /></div><div><b>Ready to hand something in?</b><span>PDF, DOCX, or image · up to 20 MB</span></div></div><form onSubmit={(event) => activeAssignment && upload(event, activeAssignment)}><label className="select-wrap"><select value={selectedAssignment ?? ''} onChange={(event) => setSelectedAssignment(Number(event.target.value) || null)}><option value="">Choose an assignment</option>{dashboard.assignments.filter((assignment) => !submissions.some((item) => item.assignment_id === assignment.id)).map((assignment) => <option value={assignment.id} key={assignment.id}>{assignment.title}</option>)}</select><ChevronDown size={15} /></label><label className="file-picker"><input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><FilePlus2 size={16} /><span>{file?.name ?? 'Choose a file'}</span></label><button className="button button-dark" disabled={busy || !activeAssignment || !file}>{busy ? 'Uploading…' : 'Submit work'} <ArrowUpRight size={15} /></button></form></div>}
      </section><aside className="panel deadlines-panel"><div className="panel-heading"><div><div className="eyebrow muted">ON THE HORIZON</div><h2>Next deadlines</h2></div><span className="calendar-mark">{new Date().getDate()}</span></div><div className="deadline-list">{dashboard.assignments.slice(0, 4).map((assignment, index) => <div className="deadline-item" key={assignment.id}><span className={`deadline-dot dot-${index % 3}`} /><div><b>{assignment.title}</b><span>{assignment.course_code}</span></div><time>{dateLabel(assignment.deadline)}</time></div>)}{dashboard.assignments.length === 0 && <div className="empty-state compact">No deadlines scheduled.</div>}</div><div className="deadline-note"><span className="note-star">✳</span><span><b>A little progress adds up.</b><small>Your coursework and feedback stay together here.</small></span></div></aside></div>
      <section className="panel submissions-panel" id="submissions"><div className="panel-heading"><div><div className="eyebrow muted">{isTeacher ? 'STUDENT WORK' : 'YOUR RECENT WORK'}</div><h2>{isTeacher ? 'Recent submissions' : 'Submission history'}</h2></div><div className="table-tools"><label className="search-box"><Search size={15} /><input placeholder="Search submissions" value={search} onChange={(event) => setSearch(event.target.value)} /></label><button className="filter-button"><Menu size={15} /> Latest <ChevronDown size={13} /></button></div></div>
        <div className="table-scroll"><table><thead><tr><th>FILE / ASSIGNMENT</th>{isTeacher && <th>STUDENT</th>}<th>SUBMITTED</th><th>STATUS</th>{isTeacher && <th>GRADE / FEEDBACK</th>}<th aria-label="Actions" /></tr></thead><tbody>{filteredSubmissions.map((submission) => <tr key={submission.id}><td><div className="file-cell"><span className="file-icon"><FileText size={17} /></span><span><b>{submission.file_name}</b><small>{submission.assignment_title} · v{submission.version} · {bytesLabel(submission.file_size)}</small></span></div></td>{isTeacher && <td><div className="student-cell"><span className="student-avatar">{submission.student_name.slice(0, 1)}</span><span>{submission.student_name}</span></div></td>}<td className="date-cell">{dateTimeLabel(submission.submitted_at)}</td><td><span className={`status-pill ${submission.status.toLowerCase()}`}>{submission.status === 'GRADED' ? 'Graded' : submission.status === 'LATE' ? 'Late' : 'Submitted'}</span></td>{isTeacher && <td>{submission.status === 'GRADED' ? <span className="grade-summary"><b>{submission.marks}</b> pts <small>{submission.feedback}</small></span> : <div className="grade-controls"><input aria-label="Marks" type="number" min="0" max={dashboard.assignments.find((item) => item.id === submission.assignment_id)?.max_marks ?? 100} placeholder="Marks" value={gradeDrafts[submission.id]?.marks ?? ''} onChange={(event) => setGradeDrafts((current) => ({ ...current, [submission.id]: { ...current[submission.id], marks: event.target.value } }))} /><input aria-label="Feedback" placeholder="Add feedback" value={gradeDrafts[submission.id]?.feedback ?? ''} onChange={(event) => setGradeDrafts((current) => ({ ...current, [submission.id]: { ...current[submission.id], feedback: event.target.value } }))} /><button title="Save grade" onClick={() => grade(submission)} disabled={busy}><Check size={15} /></button></div>}</td>}<td><button className="icon-button" title="Download submission" onClick={() => download(submission)}><ArrowDownToLine size={16} /></button></td></tr>)}{filteredSubmissions.length === 0 && <tr><td colSpan={isTeacher ? 6 : 4}><div className="empty-state table-empty">{search ? 'No submissions match your search.' : 'Your submission activity will show up here.'}</div></td></tr>}</tbody></table></div>
      </section>
      {isTeacher && <section className="panel create-panel" id="create-assignment"><div className="panel-heading"><div><div className="eyebrow muted">ADD COURSEWORK</div><h2>Publish an assignment</h2></div><span className="create-icon"><Plus size={17} /></span></div><CreateAssignment courses={courses} onCreated={async () => { setNotice('Assignment published.'); await refresh() }} onError={setError} /></section>}
      <footer className="page-footer"><span>FIELDNOTE <i>LEARNING</i></span><span><ShieldCheck size={14} /> Private class workspace</span><span>© {new Date().getFullYear()} · Built for better learning</span></footer>
    </div>
  </main></div>
}

function CreateAssignment({ courses, onCreated, onError }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [deadline, setDeadline] = useState('')
  const [courseId, setCourseId] = useState('')
  const [maxMarks, setMaxMarks] = useState('100')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault(); setBusy(true)
    try {
      await api('/assignments', { method: 'POST', body: { title, description, course_id: Number(courseId || courses[0]?.id), deadline: new Date(deadline).toISOString(), max_marks: Number(maxMarks), allowed_extensions: ['.pdf', '.docx', '.png', '.jpg', '.jpeg'], allow_resubmission: true } })
      setTitle(''); setDescription(''); setDeadline(''); await onCreated()
    } catch (err) { onError(err.message) } finally { setBusy(false) }
  }
  return <form className="create-form" onSubmit={submit}><label>Assignment title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Cloud architecture review" required minLength="3" /></label><label>Course<select value={courseId || courses[0]?.id || ''} onChange={(event) => setCourseId(event.target.value)} required>{courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.name}</option>)}</select></label><label className="span-two">Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What should students prepare?" required rows="3" /></label><label>Deadline<input type="datetime-local" value={deadline} onChange={(event) => setDeadline(event.target.value)} required /></label><label>Maximum marks<input type="number" min="1" max="1000" value={maxMarks} onChange={(event) => setMaxMarks(event.target.value)} required /></label><div className="span-two create-submit"><span>PDF, DOCX, PNG, JPG · max 20 MB</span><button className="button button-dark" disabled={busy || !courses.length}>{busy ? 'Publishing…' : 'Publish assignment'} <ArrowUpRight size={15} /></button></div></form>
}

export default Portal