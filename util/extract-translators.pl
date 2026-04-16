use strict;
use warnings;
use utf8;
use open ':std', ':encoding(UTF-8)';
use Data::Dumper;

my $start = 0;
my $credits = 0;
my $extract_re = qr{^# ([-—\w., ]+)(?: [(<].*[)>])*,? ([-—\d., ]+).?$};
my $credits_re = qr(^msgid "translator-credits\\n"$);
my %translators = ();
my $infile = shift;
my $outfile = $infile . ".new";
open(my $INFILE, "<", $infile);
open(my $OUTFILE, ">", $outfile);

while (<$INFILE>) {
    if ($_ =~ $extract_re && $start < 1) {
        $start++;
    }

    if ($start == 1) {
        my $input = $_;
        $input =~ $extract_re;
        unless ($1) {
            print $OUTFILE $_;
            $start++;
            next;
        }
        my $name = $1;
        if (exists ($translators{$name})) {
            push @{$translators{$name}}, split(", ", $2);
        } else {
            my @years =  split(", ", $2);
            $translators{$name} = \@years;
        }
    }
    if ($_ =~ $credits_re && %translators) {
        $credits++;
        print $OUTFILE $_;
        print $OUTFILE "msgstr \"\"\n";
        my @translator_list = ();
        foreach my $translator (sort(keys(%translators))) {
            my $dates = join(", ", sort(@{$translators{$translator}}));
            push @translator_list, "$translator: $dates";
        }
        my $translators_str = join("\\n ", @translator_list);
        if (defined $translators_str) {
            print $OUTFILE "\"$_\\n\"\n" for map substr($_, 0, 72), $translators_str =~ m[(.{1,72})(?:\\n |$)]g;
            print $OUTFILE "\n";
        }
    }
    $credits++ if ($credits && substr($_, 0, 1) eq "#");
    next if ($credits == 1);
    print $OUTFILE $_
}
close($INFILE);
close($OUTFILE);
rename $outfile, $infile;
=begin
    perl extract-translators.pl filename

Finds comments at the beginning of the po file of the form
  Name email-address? number
Where email-address is optional and number is one or more four-digit years separated by commas or hyphens. The name and years are extracted and replace the msgstr for msgid "translator-credits".

Run this command in a shell for loop:
   for i in po/*.po; do perl extract-translators.pl $i; done
Then review the changes and commit them.
=end
