from django import forms
from .models import InventoryMovements, LocationInventory, MovementType

class InventoryMovementForm(forms.ModelForm):
    target_location = forms.ModelChoiceField(
        queryset=LocationInventory.objects.all(),
        required=False, label = "Target Location"
    )

    class Meta:
        model = InventoryMovements
        fields = ['movement_type', 'id_material', 'id_location', 'quantity', 'cost_center', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['movement_type'].queryset=MovementType.objects.filter(symbol__in=['LOSS', 'INT_USE'])
        css_class = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#233b6e]'

        for name, field in self.fields.items():
            field.widget.attrs.update({'class':css_class})
            if name == 'description':
                field.widget.attrs.update({'rows':'3'})

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')

        if quantity <= 0:
            raise forms.ValidationError(
                "Quantity must be greater than zero."
            )

        return quantity
    
    def clean(self):
        data = super().clean()
        m_type = data.get('movement_type')
        symbol = m_type.symbol if m_type else None

        validations = {
            'INT_USE': [('cost_center', 'Critical: Cost Center is required'),
                        ('description', 'Justification required for consumption')],
            'LOSS': [('description', 'A description is required for LOSS')],
        }

        if symbol in validations:
            for field, msg in validations[symbol]:
                if not data.get(field):
                    self.add_error(field, msg)

        return data