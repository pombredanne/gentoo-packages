from django import forms
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_unicode, force_unicode
from itertools import chain

class DivCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = ['<div class="row-fluid">']
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        row1, row2 = ['<div class="span6">'], ['<div class="span6">']
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = ' for="{0}"'.format(final_attrs['id'])
            else:
                label_for = ''

            label_for += ' class="control-label"'

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = force_unicode(option_label)
            if i % 2:
                arr = row2
            else:
                arr = row1

            arr.append('<label{0}>{1} {2}</label>'.format(
                                      label_for, rendered_cb, option_label))

        row1.append('</div>')
        row2.append('</div>')
        output.extend(row1 + row2)
        output.append('</div>')
        output.append('<input type="button" id="reset" value="Reset" />')
        output.append('<input type="button" id="set" value="Set" />')
        output.append('<input type="button" id="default" value="Default" />')
        return mark_safe('\n'.join(output))

    class Media:
        js = ('js/arches_select.js',)