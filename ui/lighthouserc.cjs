module.exports = {
  ci: {
    collect: {
      staticDistDir: '../master/kosatka_master/static',
      url: ['http://localhost/admin/'],
      settings: {
        chromeFlags: '--no-sandbox --headless --disable-gpu',
      },
    },
    assert: {
      assertions: {
        'categories:performance': ['warn', {minScore: 0.7}],
        'categories:accessibility': ['warn', {minScore: 0.7}],
        'first-contentful-paint': ['warn', {maxNumericValue: 5000}],
        'interactive': ['warn', {maxNumericValue: 7000}],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
