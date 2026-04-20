import React, { useMemo } from 'react'
import './PlcMainDashboard.css'

const placeholderImage = '/images/plc-press.png'

const pressCards = [
  { id: 1, name: 'Press', image: placeholderImage, status: 'Stop', level: 'Critical', runningTime: '03:14:28' },
  { id: 2, name: 'Press', image: placeholderImage, status: 'Running', level: 'Normal', runningTime: '08:19:34' },
  { id: 3, name: 'Press', image: placeholderImage, status: 'Stop', level: 'Warning', runningTime: '12:14:57' },
  { id: 4, name: 'Press', image: placeholderImage, status: 'Running', level: 'Normal', runningTime: '14:33:00' },
  { id: 5, name: 'Press', image: placeholderImage, status: 'Running', level: 'Normal', runningTime: '11:50:12' },
  { id: 6, name: 'Press', image: placeholderImage, status: 'Running', level: 'Normal', runningTime: '09:40:09' },
]

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

function PlcMainDashboard() {
  const statusSummary = useMemo(() => {
    const running = pressCards.filter((card) => card.status === 'Running').length
    const stop = pressCards.length - running
    return { running, stop, total: pressCards.length }
  }, [])

  return (
    <section className="parsed-view plc-main-view">
      <header className="plc-main-header">
        <h2>PLC 메인 대시보드</h2>
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
              <article key={card.id} className="plc-main-press-card">
                <div className="plc-main-image-slot">
                  <img src={card.image} alt={`Press Name ${card.id} placeholder`} loading="lazy" />
                  <div className="plc-main-image-overlay">
                    <strong>{card.name}</strong>
                    <span className={`status-pill ${card.level.toLowerCase()}`}>
                      {card.level}
                    </span>
                  </div>
                </div>
                <dl className="plc-main-meta">
                  <div><dt>Status</dt><dd className={card.status === 'Running' ? 'status-running' : 'status-stop'}>{card.status}</dd></div>
                  <div><dt>Running Time</dt><dd>{card.runningTime}</dd></div>
                  <div><dt>Die Name</dt><dd>{`Die Name ${card.id}`}</dd></div>
                  <div><dt>Die Number</dt><dd>{`Die Number ${card.id}`}</dd></div>
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
