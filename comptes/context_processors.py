from django.db.models import Q

# Libellés laverie (Show ticket, Extend, Cancel) disponibles sur toutes les pages (ex. chat, nav)
LAVERIE_I18N = {
    'ru': {'show_ticket': 'Показать талон', 'extend': 'Продлить', 'cancel': 'Отменить'},
    'fr': {'show_ticket': 'Afficher le ticket', 'extend': 'Prolonger', 'cancel': 'Annuler'},
    'en': {'show_ticket': 'Show ticket', 'extend': 'Extend', 'cancel': 'Cancel'},
}


def laverie_i18n_context(request):
    """Expose laverie labels (show_ticket, extend, cancel) in all templates for consistent i18n."""
    lang = getattr(request, 'LANGUAGE_CODE', None) or 'ru'
    return {'laverie_i18n': LAVERIE_I18N.get(lang, LAVERIE_I18N['en'])}


def notifications_context(request):
    """
    Context processor pour ajouter les compteurs de notifications dans tous les templates
    """
    context = {
        'pending_orders_count': 0,
        'packaged_orders_count': 0,
        'unread_messages_count': 0,
    }
    
    if request.user.is_authenticated:
       
        from chat.models import Message, Conversation
        
        
        # Compteur de messages non lus pour tous les utilisateurs
        # Messages non lus = messages où l'utilisateur n'est pas l'expéditeur et lu=False
        conversations = Conversation.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user)
        )
        context['unread_messages_count'] = Message.objects.filter(
            Q(conversation__in=conversations) & ~Q(sender=request.user),
            lu=False
        ).count()
    
    return context

