module.exports = {
  ci: {
    collect: {
      staticDistDir: '../master/kosatka_master/static',
      url: ['http://localhost/admin/'],
    },
    assert: {
      assertions: {
        'categories:performance': ['warn', {minScore: 0.8}],
        'categories:accessibility': ['warn', {minScore: 0.8}],
        'first-contentful-paint': ['warn', {maxNumericValue: 4000}],
        'interactive': ['warn', {maxNumericValue: 6000}],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
