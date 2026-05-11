#!/usr/bin/env node
import http from 'node:http';

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
    });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (error) {
        reject(error);
      }
    });
  });
}

function start(port, handler) {
  const server = http.createServer(async (req, res) => {
    try {
      if (req.url === '/health') {
        writeJson(res, 200, { ok: true });
        return;
      }

      const payload = await readJson(req);
      const result = await handler(req.url, payload);
      writeJson(res, 200, result);
    } catch (error) {
      writeJson(res, 500, { error: String(error) });
    }
  });

  server.listen(port, '0.0.0.0', () => {
    console.log(`template mock service listening on ${port}`);
  });
}

function writeJson(res, statusCode, payload) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(payload));
}

start(8030, (_url, payload) => ({
  object: 'list',
  data: [
    {
      object: 'embedding',
      index: 0,
      embedding: Array.from({ length: 16 }, (_, index) =>
        String(payload.input ?? '').includes('通勤') && index === 0
          ? 1
          : 0.1,
      ),
    },
  ],
}));

start(8031, (_url, payload) => {
  const queryFamily = detectTemplateFamily(String(payload.query ?? ''));

  return {
    results: (payload.documents ?? []).map((document, index) => {
      const documentFamily = detectTemplateFamily(String(document));

      return {
        index,
        relevance_score:
          documentFamily && documentFamily === queryFamily
            ? 0.95
            : documentFamily
              ? 0.2
              : 0.35,
      };
    }),
  };
});

start(8032, () => ({
  choices: [
    {
      message: {
        content: JSON.stringify({
          baseFinish: 'dewy',
          eyeIntensity: 2,
          blushPlacement: 'upper_cheek',
          lipColorFamily: 'bean_paste',
          styleSignals: ['clean', 'soft_eye', 'low_saturation'],
        }),
      },
    },
  ],
}));

function detectTemplateFamily(text) {
  const source = text.normalize('NFKC').toLowerCase();
  const families = [
    {
      family: 'SPECIFIC_VISUAL',
      keywords: ['y2k', '女团', '辣妹', '上镜', 'idol', 'visual', '特定视觉'],
    },
    {
      family: 'STAGE_CREATIVE',
      keywords: ['万圣节', '朋克', '舞台', '创意', 'cosplay', '哥特'],
    },
    {
      family: 'WESTERN',
      keywords: ['欧美', '截断', '烟熏', 'cut_crease', 'sharp_contour'],
    },
    {
      family: 'CHINESE_STYLE',
      keywords: ['新中式', '国风', '复古港风', '红唇', '中式', 'retro'],
    },
    {
      family: 'ASIAN_MIXED',
      keywords: ['泰式', '混血', '亚裔', '修容', '轮廓', 'defined_eye'],
    },
    {
      family: 'ELEGANT_LUXURY',
      keywords: ['面试', '轻熟', '知性', '优雅', '千金', 'elegant', 'gentle'],
    },
    {
      family: 'KOREAN_JAPANESE_GIRL',
      keywords: ['韩系', '日系', '甜妹', '初恋', '水光', '纯欲', 'sweet'],
    },
    {
      family: 'DAILY_COMMUTE',
      keywords: ['通勤', '上班', '白开水', '清透', '日常', 'commute'],
    },
  ];

  return families.find((entry) =>
    entry.keywords.some((keyword) => source.includes(keyword)),
  )?.family;
}
