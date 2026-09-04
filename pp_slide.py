PP_SLIDE = '''<section class="slide" data-slide="4">
  <div class="atmos-bg" style="--atmos-img:url('../assets/images/bg_dark.jpg'); opacity:0.55"></div>
  <div class="pp-wrap">
    <div class="pp-header">
      <div class="eyebrow">Brand Awareness &amp; Virality</div>
      <h2 class="slide-title">Presenting <span class="accent">Partner</span></h2>
      <div class="slide-subtitle" style="max-width:860px;">Presenting Partner status puts Betclic in the name of the event &mdash; and in every asset that carries it, from the broadcast open to the final CRM send.</div>
    </div>
    <div class="pp-grid">

      <div class="pp-card">
        <div class="pp-num">01</div>
        <h3>Event Naming &amp; Identity</h3>
        <ul>
          <li>Official title lock-up &mdash; &lsquo;PFL Lyon presented by Betclic&rsquo;</li>
          <li>Co-branded event logo across every channel</li>
          <li>Named in every official mention of the event</li>
          <li>Brand quote in the announcement press release</li>
        </ul>
      </div>

      <div class="pp-card">
        <div class="pp-num">02</div>
        <h3>Broadcast</h3>
        <ul>
          <li>Logo and audio recognition on the show title card open</li>
          <li>Two welcome-back bumpers out of every commercial break</li>
          <li>Betclic presentation of all fight cards</li>
          <li>Brand mark on the fight clock &mdash; main and co-main</li>
          <li>Scripted commentator mentions across the broadcast</li>
        </ul>
      </div>

      <div class="pp-card">
        <div class="pp-num">03</div>
        <h3>In-Arena</h3>
        <ul>
          <li>PA announcer shout-outs through the card</li>
          <li>Centre canvas, cage apron and vertical bumper</li>
          <li>LED ribbon and big-screen takeovers between fights</li>
          <li>Branded step-and-repeat at press conference and weigh-in</li>
        </ul>
      </div>

      <div class="pp-card">
        <div class="pp-num">04</div>
        <h3>Social</h3>
        <ul>
          <li>Co-branded event announcement across PFL channels</li>
          <li>Presented-by tag on every event post</li>
          <li>Fight-week content series</li>
          <li>Post-event highlight reel presented by Betclic</li>
        </ul>
      </div>

      <div class="pp-card">
        <div class="pp-num">05</div>
        <h3>CRM &amp; Owned Media</h3>
        <ul>
          <li>Dedicated email blast to the PFL database in territory</li>
          <li>Presenting-partner banner across the full event email flow</li>
          <li>PFL app push notification on fight day</li>
          <li>Event page and ticketing-flow branding with click-through</li>
        </ul>
      </div>

      <div class="pp-card">
        <div class="pp-num">06</div>
        <h3>Promotions &amp; Access</h3>
        <ul>
          <li>Ticket ballots and fan giveaways</li>
          <li>Co-promoted sign-up offer around the event</li>
          <li>Money-can&rsquo;t-buy experiences for top players</li>
          <li>VIP and GA allocation, backstage and weigh-in access</li>
        </ul>
      </div>

    </div>
  </div>
  <div class="slide-num">04 / 19</div>
</section>

'''

PP_CSS = '''
/* Presenting Partner asset grid — slide 4 (Awareness) */
.pp-wrap {
    position: relative;
    z-index: 2;
    height: 100%;
    padding: 46px 80px 54px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.pp-header {
    text-align: center;
    margin-bottom: 26px;
}
.pp-header .slide-subtitle {
    margin-left: auto;
    margin-right: auto;
}
.pp-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    width: 100%;
    max-width: 1180px;
    margin: 0 auto;
    align-items: stretch;
}
.pp-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 2px solid var(--ls-green);
    border-radius: 4px;
    padding: 15px 18px 17px;
}
.pp-num {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.08em;
    color: var(--ls-green);
    margin-bottom: 5px;
}
.pp-card h3 {
    font-family: var(--font-cond);
    font-weight: 600;
    font-size: 15px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #fff;
    margin: 0 0 10px;
}
.pp-card ul { margin: 0; padding: 0; list-style: none; }
.pp-card li {
    position: relative;
    padding-left: 14px;
    font-size: 12.5px;
    line-height: 1.5;
    color: rgba(255,255,255,0.66);
    margin-bottom: 6px;
}
.pp-card li:last-child { margin-bottom: 0; }
.pp-card li::before {
    content: '';
    position: absolute;
    left: 0;
    top: 7px;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--ls-green);
}
@media (max-width: 1100px) {
    .pp-wrap { padding: 34px 40px 44px; }
    .pp-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
}
@media (max-width: 700px) {
    .pp-grid { grid-template-columns: 1fr; }
    .pp-card li { font-size: 12px; }
}
'''
