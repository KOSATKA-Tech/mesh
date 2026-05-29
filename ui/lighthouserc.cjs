module.exports = {
  ci: {
    collect: {
      staticDistDir: '../master/kosatka_master/static',
      url: ['http://localhost/admin/'],
    },
    assert: {
      assertions: {
        'categories:performance': ['error', {minScore: 0.8}], // Relaxed slightly for CI runners
        'categories:accessibility': ['error', {minScore: 0.9}],
        'first-contentful-paint': ['warn', {maxNumericValue: 3000}],
        'interactive': ['error', {maxNumericValue: 5000}],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};

