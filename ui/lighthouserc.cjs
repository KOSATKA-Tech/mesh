module.exports = {
  ci: {
    collect: {
      staticDistDir: '../master/kosatka_master/static',
      startServerCommand: 'npm run preview',
      url: ['http://localhost:4173/admin/'],
    },
    assert: {
      assertions: {
        'categories:performance': ['error', {minScore: 0.9}],
        'categories:accessibility': ['error', {minScore: 0.9}],
        'first-contentful-paint': ['warn', {maxNumericValue: 2000}],
        'interactive': ['error', {maxNumericValue: 3500}],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
