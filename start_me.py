
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import os
import numpy as np


app = Flask(__name__, static_folder = '')
app.config['UPLOAD_FOLDER'] = 'uploads'  # te man būs ielādētie faili 
app.config['MAP_IMAGES'] = 'images' 
app.config['ALLOWED_EXTENSIONS'] = {'csv'}   # man ir svarīgi, lai faili ir tikai csv. 
app.secret_key = 'mans_projekts' 

# url_for('static', filename='style.css') Es vēl izdomāšu, vai likt css vai atstāt formātus katrā html.

@app.route("/")
def view_csv():
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'team_list.csv')
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, delimiter=';', dtype={'id':str, 'Vieta': str, 'Punkti': str, 'Sods': str, 'Papildus':str, 'Rezultāts':str})  # ielādējam komandu sarakstu ar pandām
        #te būs datu pārveide.
        #man vajag, lai komandas nosaukums strādā kā links un /team lapu ar id no pirmās kolonnas kā parametru
        #tad man vajag, lai komandas grupa un vieta grupā ir apvienoti vienā kolonnā
        #rezultātam jābūt skaidri redzamam
        #rezultāta veidošanās skaidrojums tikai, ja ir sodi vai papildus
        if 'Vieta grupā' in df.columns and 'Vieta' in df.columns:
            df['Vieta klasē'] = df['Vieta grupā'] + ':' + df['Vieta']   #apvieno vietu grupā ar vietas numuru, piem XO2 un 3. vieta
        
        if 'ID' in df.columns and 'Nosaukums' in df.columns:
            df['Nosaukums'] = df.apply(lambda row: f'<a href="/team/{row["ID"]}">{row["Nosaukums"]}</a>', axis=1)   #tiek izveidots links zem nosaukuma
        
        if 'Sods' in df.columns and 'Papildus' in df.columns and 'Punkti' in df.columns:
            df.loc [(df['Sods'] != '0') & (df['Papildus'] != '0'), 'Skaidrojums'] = '(' + df['Punkti'] + df['Sods'] +  df['Papildus'] + '=' + df['Rezultāts'] + ')'
            df.loc [(df['Sods'] != '0') & (df['Papildus'] == '0'), 'Skaidrojums'] = '(' + df['Punkti'] + df['Sods'] + '=' + df['Rezultāts'] + ')'
            df.loc [(df['Sods'] == '0') & (df['Papildus'] == '0'), 'Skaidrojums'] = ''   #skaidrojums kāpēc punkti nav kā rezultāts
        
        return render_template('main_teams.html', tables=df.to_html(classes='data', escape=False, header=True, index=False, columns=['Nosaukums','Distance','Vieta klasē', 'Rezultāts', 'Skaidrojums', 'Laiks'], na_rep=''))
    else:  
        return render_template ('main.html')   #monty python lapa


# Pārliecināties, ka uploada folderi eksistē
with app.app_context():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']   #pārbauda vai fails ir atļauts

@app.route('/admin', methods=['GET', 'POST'])
def admin():

    if request.method == 'POST':
        for file_key in ['team_list', 'team_splits', 'coord2']:
            if file_key in request.files and request.files[file_key]:
                file = request.files[file_key]
                if allowed_file(file.filename):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_key}.csv')
                    file.save(file_path)
                    flash(f'✅ {file_key}.csv veiksmīgi ielādēts!', 'success')
                else:
                    flash(f'❌ Nepareizs faila tips {file_key} failam. Der tikai CSV. Un ar vajadzīgajām kolonnām...', 'danger')
        return redirect(url_for('admin'))

    files = {f: os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], f)) for f in ['team_list.csv', 'team_splits.csv', 'coord2.csv']}
    
    return render_template('admin.html', files = files)  #šis atgriezīs admin sadaļas lapu, cerams.


@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f'🗑️ {filename} izdzēsu!', 'success')
    else:
        flash(f'❌ {filename} neatradu...', 'danger')
    return redirect(url_for('admin'))


@app.route ('/team/<id>', methods=['GET'])  #sarežģītākā vieta visā lapā...
def draw_team(id):

    import matplotlib
    from matplotlib import pyplot as plt
    matplotlib.use('agg')


    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'coord2.csv')
    coordpanda = pd.read_csv (file_path, delimiter=';') #kp koordinātas, droši vien būtu jāielādē kaut kur agrāk? admin?

    file_path1 = os.path.join(app.config['UPLOAD_FOLDER'], 'team_splits.csv')   #norāda kur komanda ir bijusi
    file_path2 = os.path.join(app.config['UPLOAD_FOLDER'], 'team_list.csv')    #splitos neparādās komandu nosaukums, priekš tam ir šis


    if os.path.exists(file_path1):  #ja ir ielādēti spliti
        
        spliti = pd.read_csv (file_path1, delimiter=';',dtype={'1': str} ) #komandu spliti
        spliti ['Previous CP']= spliti['KP'].shift(1)
        
        splitpanda = spliti[spliti['1']== id] #komandu spliti, atlasīti pēc komandas id
        

        teams = pd.read_csv (file_path2, delimiter=';' ,dtype={'ID': str})  #vai tiešām man viņš ir jāielādē no jauna, ja jau citā app vietā bija ielādēts?
        team_data = teams[teams['ID']==id] # komandu dati, atlasīti pēc komandas id, vajadzētu te būt tikai 1 rindai
        kom_kp = pd.merge (splitpanda, coordpanda, left_on='KP', right_on='tehnr', how = 'inner')   #saliek savāktos punktus ar koordinātēm

        
        #te es mēģinu izdabūt komandas grafiku uz matplotlib, tam fonā pieliekot attēlu ar karti
        file_path4 = os.path.join(app.config['UPLOAD_FOLDER'], 'karte.jpg')
        img = plt.imread(file_path4)

        fig, ax = plt.subplots()
        ax.imshow(img, extent=[39, 228, -240, -66])   #nākotnē vajadzētu likt karti caur admin un kartes stūru koordinātes
        
        #plt.plot ([12, 36], [99,140])    

        plt.axis('off') #nerādīt skalu
        # šeit piedzenu tā, lai attēla KP sakristu ar koordināšu KP. čakars, bet ok.

        count = 1 #ierakstus skaitīsim

        for line in kom_kp:    
            count += 1 #apstrādājam rindu nr2 utt.
            plt.plot (kom_kp['x'], kom_kp['y'], color = 'magenta', marker = '.')   #uzzīmē grafiku
            #plt.plot ([kom_kp.loc[count-1]['x'],kom_kp.loc[count]['x']], [kom_kp.loc[count-1]['y'],kom_kp.loc[count]['y']], color = 'magenta', marker = '.')
                    
        txt = id
        nosaukums = team_data['Nosaukums'].iloc[0]
        virsraksts = 'Komandas ' + nosaukums + ' grafiks'
        plt.title (virsraksts)
        filename = txt  #grafiku nosaucam atbilstoši komandas id
        file_path3 = 'images' + '/' + id + '.png' 
        #file_path3 = os.path.join(app.config['MAP_IMAGES'], f"{id}.png")
        #.replace("\\","/")
        #file_path5 = url_for ('static',  filename=file_path3)
        #nammme = id +'.png'
        plt.savefig(file_path3, bbox_inches='tight', dpi=250 ) 
        #print ('Izeksportēju smthing')
        plt.close(fig)
        attels = filename + '.png'
        return render_template('split_teams.html', name = id, url=file_path3,  tables=splitpanda.to_html(classes='data', escape=False, header=True, index=False,  na_rep=''))
    else:
        return render_template ('splits_missing.html')   #atgriežam, ja nav spliti




if __name__ == '__main__':
    app.run(debug=True)