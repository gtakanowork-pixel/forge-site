document.addEventListener('DOMContentLoaded', () => {
  const items = [...document.querySelectorAll('[data-points]')];
  const score = document.querySelector('#score');
  const result = document.querySelector('#result');
  const none = document.querySelector('#audit-none');
  if (!score || !result || items.length !== 5 || !none) return;

  const selected = (index) => items[index].getAttribute('aria-checked') === 'true';
  const noMatches = () => none.getAttribute('aria-checked') === 'true';
  const copyButton = document.querySelector('#copy-audit');
  const copyStatus = document.querySelector('#copy-status');
  const render = () => {
    const hasSelection = noMatches() || items.some((_, index) => selected(index));
    const points = items.reduce((sum, item, index) => sum + (selected(index) ? Number(item.dataset.points) : 0), 0);
    score.textContent = hasSelection ? String(points) : '—';
    if (copyButton) copyButton.disabled = !hasSelection;
    if (copyStatus) copyStatus.textContent = '';
    if (!hasSelection) {
      result.textContent = '該当する項目を選択してください。当てはまる項目がない場合は「どれも当てはまらない」を選択してください。';
      return;
    }

    // Safety gates take priority over the numeric score.
    if (selected(4)) {
      result.textContent = '失敗時の影響が重大な業務です。合計点にかかわらず無人での自動化は勧めません。人の承認・監査・復旧手順を先に設計してください。';
    } else if (selected(3)) {
      result.textContent = '高度な判断が必要な業務です。合計点にかかわらず判断の自動化は勧めません。下書き・情報整理など、人が確認できる補助に限定して検討してください。';
    } else if (points >= 4) {
      result.textContent = '自動化を具体検討する価値があります。まず影響の小さい1業務から、人が確認できる形で試してください。';
    } else if (points >= 1) {
      result.textContent = '全部を自動化せず、一部の補助から試すのが候補です。';
    } else {
      result.textContent = '現時点では無理に自動化しない判断も合理的です。';
    }
  };

  items.forEach(item => item.addEventListener('click', () => {
    const next = item.getAttribute('aria-checked') !== 'true';
    item.setAttribute('aria-checked', String(next));
    if (next) none.setAttribute('aria-checked', 'false');
    render();
  }));
  // Explicitly distinguish 'none apply' from an unanswered checklist.
  none.addEventListener('click', () => {
    const next = none.getAttribute('aria-checked') !== 'true';
    none.setAttribute('aria-checked', String(next));
    if (next) items.forEach(item => item.setAttribute('aria-checked', 'false'));
    render();
  });
  // Sharing is initiated only by the visitor. No result is sent to Forge.
  copyButton?.addEventListener('click', async () => {
    const summary = [
      'Forge | AI業務自動化の3分セルフ診断',
      `判定: ${score.textContent}点`,
      result.textContent,
      '無料診断: https://gtakanowork-pixel.github.io/forge-site/ai-automation-audit.html'
    ].join('\n');
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(summary);
      if (copyStatus) copyStatus.textContent = '診断結果をコピーしました。共有先への貼り付けはご自身で行ってください。';
    } catch {
      if (copyStatus) copyStatus.textContent = 'このブラウザではコピーできません。画面の判定文を選択してコピーしてください。';
    }
  });
  document.querySelector('#reset-audit')?.addEventListener('click', () => {
    items.forEach(item => item.setAttribute('aria-checked', 'false'));
    none.setAttribute('aria-checked', 'false');
    render();
  });
  render();
});
