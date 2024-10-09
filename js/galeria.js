$(document).ready(function() {
    // Filtrar imágenes por categoría
    $('.custom-filter-btn').click(function() {
        var filter = $(this).data('filter');

        if (filter == 'all') {
            $('.custom-gallery-item').show();
        } else {
            $('.custom-gallery-item').hide();
            $('.custom-gallery-item[data-category="' + filter + '"]').show();
        }
    });

    // Abrir modal y mostrar imagen
    $('.custom-img-wrapper').click(function() {
        var imgSrc = $(this).find('img').attr('src');
        $('#customModalImage').attr('src', imgSrc);
        $('#customImageModal').modal('show');
    });
});
