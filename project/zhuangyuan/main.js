import { DEFAULT_BOARD, promoteZhuangyuan } from "./board.js";

const rankTitles = ["状元", "榜眼", "探花", "传胪", "进士", "进士", "进士", "进士", "进士", "进士"];
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let board = [...DEFAULT_BOARD];
let ceremonyId = 0;
let isAnimating = false;
let timers = [];

const rankList = document.querySelector("#rank-list");
const form = document.querySelector("#ceremony-form");
const input = document.querySelector("#candidate-name");
const button = document.querySelector("#open-button");
const errorText = document.querySelector("#form-error");
const flyingName = document.querySelector("#flying-name");
const openingEdict = document.querySelector("#opening-edict");
const boardPanel = document.querySelector("#board-panel");
const resultToast = document.querySelector("#result-toast");
const redSilk = document.querySelector("#red-silk");
const dropSeal = document.querySelector("#drop-seal");
const particleField = document.querySelector("#particle-field");

function clearTimers() {
  timers.forEach((timer) => window.clearTimeout(timer));
  timers = [];
}

function queue(delay, callback) {
  const actualDelay = prefersReducedMotion ? Math.max(60, delay * 0.25) : delay;
  timers.push(window.setTimeout(callback, actualDelay));
}

function centerOf(element) {
  const rect = element.getBoundingClientRect();
  return {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  };
}

function renderBoard() {
  rankList.innerHTML = board
    .map((entry, index) => {
      const rank = index + 1;
      const champion = index === 0;

      return `
        <li class="rank-row ${champion ? "champion-row" : ""}" data-rank="${rank}">
          <span class="rank-number">第 ${rank} 名</span>
          <span class="rank-medal">${rankTitles[index]}</span>
          <span class="rank-name">${entry.name}</span>
          ${
            champion
              ? '<span class="champion-seal">冠 新科状元</span>'
              : '<span class="rank-flourish" aria-hidden="true"></span>'
          }
        </li>
      `;
    })
    .join("");
}

function createParticles() {
  particleField.innerHTML = "";

  for (let index = 0; index < 48; index += 1) {
    const particle = document.createElement("span");
    particle.style.setProperty("--angle", `${index * 17 + (index % 5) * 11}deg`);
    particle.style.setProperty("--distance", `${72 + (index % 9) * 12}px`);
    particle.style.setProperty("--delay", `${(index % 8) * 0.035}s`);
    particle.style.setProperty("--size", `${3 + (index % 4)}px`);
    particleField.append(particle);
  }
}

function resetEffects() {
  document.body.classList.remove("ceremony-opening", "ceremony-landing", "ceremony-done");
  flyingName.classList.remove("is-visible");
  redSilk.classList.remove("is-visible");
  dropSeal.classList.remove("is-visible");
  resultToast.classList.remove("is-visible");
  boardPanel.classList.remove("board-shake");
  particleField.innerHTML = "";
}

function animateRankShift(nextBoard) {
  const firstRects = new Map(
    [...rankList.querySelectorAll(".rank-row")].map((row) => [row.querySelector(".rank-name").textContent, row.getBoundingClientRect()]),
  );

  board = nextBoard;
  renderBoard();

  [...rankList.querySelectorAll(".rank-row")].forEach((row, index) => {
    const name = row.querySelector(".rank-name").textContent;
    const first = firstRects.get(name);
    const last = row.getBoundingClientRect();

    if (first) {
      const deltaY = first.top - last.top;
      row.animate(
        [
          { transform: `translateY(${deltaY}px)`, opacity: 0.92 },
          { transform: "translateY(0)", opacity: 1 },
        ],
        {
          duration: prefersReducedMotion ? 80 : 520,
          easing: "cubic-bezier(.2,.8,.2,1)",
        },
      );
    } else if (index === 0) {
      row.animate(
        [
          { transform: "translateY(-28px) scale(.96)", opacity: 0 },
          { transform: "translateY(0) scale(1)", opacity: 1 },
        ],
        {
          duration: prefersReducedMotion ? 80 : 560,
          easing: "cubic-bezier(.2,.8,.2,1)",
        },
      );
    }
  });
}

function flyNameToChampion(name) {
  const from = centerOf(input);
  const championRow = rankList.querySelector(".rank-row");
  const to = centerOf(championRow);

  flyingName.querySelector("strong").textContent = name;
  flyingName.style.left = `${from.x}px`;
  flyingName.style.top = `${from.y}px`;
  flyingName.classList.add("is-visible");

  flyingName.animate(
    [
      { left: `${from.x}px`, top: `${from.y}px`, transform: "translate(-50%, -50%) scale(.64) rotate(-7deg)", opacity: 0 },
      { left: `${(from.x + to.x) / 2}px`, top: `${Math.min(from.y, to.y) - 96}px`, transform: "translate(-50%, -50%) scale(1.18) rotate(4deg)", opacity: 1 },
      { left: `${to.x}px`, top: `${to.y}px`, transform: "translate(-50%, -50%) scale(.96) rotate(0)", opacity: 1 },
    ],
    {
      duration: prefersReducedMotion ? 120 : 900,
      easing: "cubic-bezier(.17,.84,.44,1)",
      fill: "forwards",
    },
  );
}

function setFormLocked(locked) {
  isAnimating = locked;
  input.disabled = locked;
  button.disabled = locked || !input.value.trim();
  button.textContent = locked ? "卷 开榜中" : "✧ 开榜";
  button.setAttribute("aria-busy", String(locked));
}

function openBoard(event) {
  event.preventDefault();

  const name = input.value.trim();
  if (!name || isAnimating) {
    errorText.textContent = name ? "" : "请先写下你的姓名";
    return;
  }

  clearTimers();
  resetEffects();
  ceremonyId += 1;
  errorText.textContent = "";
  setFormLocked(true);
  document.body.classList.add("ceremony-opening");

  queue(760, () => {
    document.body.classList.remove("ceremony-opening");
    flyNameToChampion(name);
  });

  queue(1660, () => {
    const nextBoard = promoteZhuangyuan(board, name, ceremonyId);
    animateRankShift(nextBoard);
    flyingName.classList.remove("is-visible");
    document.body.classList.add("ceremony-landing");
    boardPanel.classList.add("board-shake");
    redSilk.classList.add("is-visible");
    dropSeal.classList.add("is-visible");
    createParticles();
  });

  queue(2860, () => {
    document.body.classList.remove("ceremony-landing");
    document.body.classList.add("ceremony-done");
    resultToast.classList.add("is-visible");
    setFormLocked(false);
    input.value = "";
    button.disabled = true;
  });
}

input.addEventListener("input", () => {
  errorText.textContent = "";
  button.disabled = isAnimating || !input.value.trim();
});

form.addEventListener("submit", openBoard);
window.addEventListener("beforeunload", clearTimers);

renderBoard();
