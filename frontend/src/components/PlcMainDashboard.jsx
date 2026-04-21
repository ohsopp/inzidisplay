import React, { useMemo } from 'react'
import './PlcMainDashboard.css'

const placeholderImage = '/images/plc-press.png'

/** PLC 대시보드와 동일한 치명 경고 M 비트 (활성 시 Critical 배지 근거) */
const CRITICAL_WARNING_KEYS = [
  'emergencyStopRF_M300',
  'emergencyStopLF_M301',
  'emergencyStopRR_M302',
  'emergencyStopLR_M303',
  'cBPumpMotorTrip_M327',
  'cBCoolingMotorTrip_M328',
  'pressOverload_M334',
  'overrun_M339',
  'safetyBlock_M329',
]

function toUnsigned(num, len) {
  const bits = Number(len) || 32
  const u32 = Number(num) >>> 0
  if (bits <= 8) return u32 & 0xff
  if (bits <= 16) return u32 & 0xffff
  return u32
}

function decodePackedBcdFromUnsigned(u, bits) {
  const nibbleCount = Math.max(1, Math.floor((Number(bits) || 16) / 4))
  const hex = Number(u).toString(16).padStart(nibbleCount, '0').slice(-nibbleCount)
  if (!/^[0-9]+$/.test(hex)) return null
  return Number(hex)
}

function toSigned32FromUnsigned(u) {
  const v = Number(u) >>> 0
  return v >= 0x80000000 ? v - 0x100000000 : v
}

function decodeMetricValue(raw, info) {
  if (raw === '-' || raw === undefined || raw === null || !info) return null
  const dt = String(info?.dataType || '').toLowerCase()
  const scale = parseFloat(String(info?.scale ?? '1')) || 1
  const len = Number(info?.length) || 32
  const num = Number(raw)
  if (!Number.isFinite(num)) return null
  if (dt === 'word' || dt === 'dword') {
    const u = dt === 'dword' ? toUnsigned(num, 32) : toUnsigned(num, len)
    if (dt === 'dword' && String(info?.description || '').includes('-값으로 표현')) {
      return toSigned32FromUnsigned(u) * scale
    }
    const isBcdMarked = /BCD/i.test(String(info?.description || ''))
    const bcd = isBcdMarked ? decodePackedBcdFromUnsigned(u, len) : null
    const base = bcd !== null ? bcd : u
    return base * scale
  }
  if (dt === 'boolean') return Number(Boolean(num))
  return num * scale
}

function toFiniteNumber(value) {
  if (value === '-' || value === undefined || value === null) return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function formatRunningTimeParts(hour, min, sec) {
  const h = toFiniteNumber(hour)
  const m = toFiniteNumber(min)
  const s = toFiniteNumber(sec)
  if (h === null && m === null && s === null) return '—'
  const pad = (n, fallback) => String(Math.max(0, Math.floor(n ?? fallback))).padStart(2, '0')
  return `${pad(h, 0)}:${pad(m, 0)}:${pad(s, 0)}`
}

function Donut({ running, stop, total }) {
  const runningDeg = total > 0 ? (running / total) * 360 : 0
  return (
    <div
      className="plc-main-donut"
      style={{
        background: `conic-gradient(#64d9a6 0deg ${runningDeg}deg, #fb7185 ${runningDeg}deg 360deg)`,
      }}
    >
      <div className="plc-main-donut-inner" />
      <span className="plc-main-donut-total">{total}</span>
    </div>
  )
}

function PlcMainDashboard({ mcValues = {}, ioVariableList = [], onNavigateToPlc }) {
  const infoByName = useMemo(() => Object.fromEntries(ioVariableList), [ioVariableList])

  const getTextByCandidates = (names) => {
    for (const name of names) {
      const raw = mcValues[name]
      if (raw === undefined || raw === null || raw === '-') continue
      const text = String(raw).replace(/\0+$/, '').trim()
      if (text) return text
    }
    return '-'
  }

  const getMetricByCandidates = (names) => {
    for (const name of names) {
      const info = infoByName[name]
      if (!info) continue
      const decoded = decodeMetricValue(mcValues[name], info)
      if (decoded !== null) return decoded
    }
    return null
  }

  const pressCards = useMemo(() => {
    const currentDieName = getTextByCandidates(['currentDieName_D1560'])
    const currentDieNo = getMetricByCandidates(['currentDieNumber_D140'])
    const spm = getMetricByCandidates(['strokePerMinute_D126', 'cPMCyclePerMinute_D104'])
    const runningHour = getMetricByCandidates(['todayRunningTimeHour_D1056', 'todayRunningTimeHour_D1057'])
    const runningMin = getMetricByCandidates(['todayRunningTimeMin_D1058', 'todayRunningTimeMin_D1059'])
    const runningSec = getMetricByCandidates(['todayRunningTimeSec_D1054', 'todayRunningTimeSec_D1055'])

    const spmNum = toFiniteNumber(spm)
    const isRunning = spmNum !== null && spmNum > 0
    const hasCriticalAlarm = CRITICAL_WARNING_KEYS.some((k) => Number(mcValues[k]) === 1)

    let level = 'Warning'
    if (isRunning) level = 'Normal'
    else if (hasCriticalAlarm) level = 'Critical'

    const dieNoLabel = currentDieNo !== null && currentDieNo !== undefined
      ? String(Math.trunc(Number(currentDieNo)))
      : '—'

    const card1 = {
      id: 1,
      overlayTitle: 'Press',
      image: placeholderImage,
      status: isRunning ? 'Running' : 'Stop',
      level,
      runningTime: formatRunningTimeParts(runningHour, runningMin, runningSec),
      dieName: currentDieName,
      dieNumberLabel: dieNoLabel,
    }

    const staticMiddle = [
      { id: 2, overlayTitle: 'Press', image: placeholderImage, status: 'Running', level: 'Normal', runningTime: '08:19:34' },
      { id: 3, overlayTitle: 'Press', image: placeholderImage, status: 'Stop', level: 'Warning', runningTime: '12:14:57' },
      { id: 4, overlayTitle: 'Press', image: placeholderImage, status: 'Running', level: 'Normal', runningTime: '14:33:00' },
      { id: 5, overlayTitle: 'Press', image: placeholderImage, status: 'Running', level: 'Normal', runningTime: '11:50:12' },
    ].map((c) => ({
      ...c,
      dieName: `Die Name ${c.id}`,
      dieNumberLabel: String(c.id),
    }))

    const card6 = {
      id: 6,
      overlayTitle: 'Press',
      image: placeholderImage,
      status: 'Stop',
      level: 'Critical',
      runningTime: '00:00:00',
      dieName: 'Die Name 6',
      dieNumberLabel: '6',
    }

    return [card1, ...staticMiddle, card6]
  }, [mcValues, infoByName])

  const statusSummary = useMemo(() => {
    const running = pressCards.filter((card) => card.status === 'Running').length
    const stop = pressCards.length - running
    return { running, stop, total: pressCards.length }
  }, [pressCards])

  return (
    <section className="parsed-view plc-main-view">
      <header className="plc-main-header">
        <h2>PLC 대시보드</h2>
      </header>

      <div className="plc-main-body">
        <article className="plc-main-section plc-main-status">
          <div className="plc-main-section-head">
            <h3>Operating Status</h3>
          </div>
          <div className="plc-main-status-content">
            <Donut running={statusSummary.running} stop={statusSummary.stop} total={statusSummary.total} />
            <div className="plc-main-status-legend">
              <div><i className="dot running" />Running <strong>{statusSummary.running}</strong></div>
              <div><i className="dot stop" />Stop <strong>{statusSummary.stop}</strong></div>
              <div><span>Total</span> <strong>{statusSummary.total}</strong></div>
            </div>
          </div>
        </article>

        <article className="plc-main-section">
          <div className="plc-main-section-head">
            <h3>Overview</h3>
          </div>
          <div className="plc-main-card-grid">
            {pressCards.map((card) => (
              <article
                key={card.id}
                className={`plc-main-press-card${onNavigateToPlc ? ' plc-main-press-card--nav' : ''}`}
                role={onNavigateToPlc ? 'button' : undefined}
                tabIndex={onNavigateToPlc ? 0 : undefined}
                onClick={onNavigateToPlc}
                onKeyDown={
                  onNavigateToPlc
                    ? (e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          onNavigateToPlc()
                        }
                      }
                    : undefined
                }
                aria-label={onNavigateToPlc ? 'PLC 대시보드로 이동' : undefined}
              >
                <div className="plc-main-image-slot">
                  <img src={card.image} alt={`Press ${card.id}`} loading="lazy" />
                  <div className="plc-main-image-overlay">
                    <strong>{card.overlayTitle}</strong>
                    <span className={`status-pill ${card.level.toLowerCase()}`}>
                      {card.level}
                    </span>
                  </div>
                </div>
                <dl className="plc-main-meta">
                  <div><dt>Status</dt><dd className={card.status === 'Running' ? 'status-running' : 'status-stop'}>{card.status}</dd></div>
                  <div><dt>Running Time</dt><dd>{card.runningTime}</dd></div>
                  <div><dt>Die Name</dt><dd>{card.dieName}</dd></div>
                  <div><dt>Die Number</dt><dd>{card.dieNumberLabel}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        </article>
      </div>
    </section>
  )
}

export default PlcMainDashboard
