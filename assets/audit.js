document.addEventListener('DOMContentLoaded', () => {
  const items = [...document.querySelectorAll('[data-points]')];
  const score = document.querySelector('#score');
  const result = document.querySelector('#result');
  if (!score || !result || items.length !== 5) return;

  const selected = (index) => items[index].getAttribute('aria-checked') === 'true';
  const render = () => {
    const points = items.reduce((sum, item, index) => sum + (selected(index) ? Number(item.dataset.points) : 0), 0);
    score.textContent = String(points);

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
    item.setAttribute('aria-checked', String(item.getAttribute('aria-checked') !== 'true'));
    render();
  }));
  document.querySelector('#reset-audit')?.addEventListener('click', () => {
    items.forEach(item => item.setAttribute('aria-checked', 'false'));
    render();
  });
  render();
});
