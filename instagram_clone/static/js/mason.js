
 window.onload = () => {
    const grid = document.querySelector('.post-container');
    const masonry = new Masonry(grid,{
        itemSelector: '.post-item',
        columnWidth:80,
        gutter: 20, //padding
        originLeft: false,
        // originTop: false,
    });
};
  
  