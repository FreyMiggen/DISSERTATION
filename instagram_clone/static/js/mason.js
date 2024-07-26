
 window.onload = () => {
    const grid = document.querySelector('.post-container');
    const masonry = new Masonry(grid,{
        itemSelector: '.post-item',
        columnWidth:150,
        gutter: 30, //padding
        originLeft: false,
        // originTop: false,
    });
};
  
  